import socket
from typing import List

from logger import get_logger
from user import User, CurrentUser

BUFFER_SIZE = 1024
server_hostname = 'vega.ii.uam.es'
server_port = 8000


class RegisterFailed(Exception):
    def __init__(self):
        super().__init__("Register failed")


class UserUnknown(Exception):
    def __init__(self, nick: str):
        super().__init__(f"User {nick} was not found")


class BadUser(Exception):
    def __init__(self, nick: str):
        super().__init__(f"Couldn't parse {nick} information")


def _send(message: bytes, end_char: chr = None) -> str:
    """
    Sends a message to the Discovery Server
    :param message: message encoded in bytes to be sent
    :return: response of the server
    """
    return_string = ""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as connection:
        connection.connect((socket.gethostbyname(server_hostname), server_port))
        connection.send(message)
        get_logger().debug(f"Sent {message} to discovery server")
        response = connection.recv(BUFFER_SIZE)
        return_string += response.decode()
        if end_char:
            connection.setblocking(False)
            while chr(response[-1]) != end_char:
                try:
                    response = connection.recv(BUFFER_SIZE)
                    return_string += response.decode()
                except BlockingIOError:
                    pass
        connection.send("QUIT".encode())

    get_logger().debug(f"Received {return_string} from discovery server")
    return return_string


def register():
    """
    Registers the current user in the system with the specified parameters
    :raise RegisterFailed
    """
    user = CurrentUser()
    string_to_send = f"REGISTER {user.nick} {user.ip} {user.tcp_port} {user.password} {'#'.join(user.protocols)}"
    response = _send(string_to_send.encode()).split()
    if response[0] == "NOK":
        get_logger().warning(f"Error registering user {user.nick}: {response}")
        raise RegisterFailed
    get_logger().info(f"Successfully registered user {user.nick}")


def get_user(nick: str) -> User:
    """
    Gets the IP, port and protocols of the user with the specified nickname
    :param nick
    :return: User
    :raise UserUnknown if user is not found
    """
    string_to_send = f"QUERY {nick}"
    response = _send(string_to_send.encode()).split()
    if response[0] == "NOK":
        get_logger().warning(f"Error getting username: {response}")
        raise UserUnknown(nick)
    else:
        try:
            user = User(nick, ip=response[3], tcp_port=int(response[4]), protocols=response[5])
            get_logger().info(f"Successfully fetched user {nick}")
            return user
        except Exception:
            get_logger().warning(f"Error getting username: {response}")
            raise BadUser(nick)


def list_users() -> List[User]:
    """
    Gets a list of all the users
    :return: list of users.
    """
    """Response contains something like OK USERS_LIST N_USERS user1#... So to get the actual list of users, 
        we look for N_USERS and start splitting the list from there. Afterwards, we get a list with all the info
        of each user in a string (users_str), so we need to split again each user to get a list of the needed values"""

    response = _send("LIST_USERS".encode(), end_char='#')
    n_users = response.split()[2]
    start_index = response.find(n_users) + len(n_users) + 1  # The number itself and the white space
    users_str = response[start_index:].split('#')[:-1]  # Avoid final empty element
    users_splitted = [user.split() for user in users_str]

    users = []
    for user in users_splitted:
        try:
            # Protocols is not answered by the server, ts instead. Since we do not use the info, we set it to V0
            users.append(User(nick=user[0], ip=user[1], tcp_port=int(float(user[2])), protocols="V0"))
        except Exception as e:
            get_logger().warning(f"Error parsing user: {e}")
            pass

    get_logger().info(f"Successfully parsed {len(users)} users out of {n_users}")
    return users
