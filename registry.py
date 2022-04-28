import os.path
from socket import *
from threading import *

# A dictionary for holding the usernames and passwords
user_information = dict()
ui_lock = Lock()

# A dictionary for online users (their usernames and IP addresses)
online_users = dict()
ou_lock = Lock()

peer_server_port = 23456


# noinspection DuplicatedCode
def main():
    if not os.path.isdir('log_registry'):
        os.mkdir('log_registry')

    server_port = 12345
    server_socket = socket(AF_INET, SOCK_STREAM)
    server_socket.bind(('', server_port))
    server_socket.listen()

    while True:
        connection_socket, client_address = server_socket.accept()
        thread = Thread(target=handle_client, args=(connection_socket, client_address[0]))
        thread.start()


def handle_client(connection_socket, client_ip):
    file_path = f'log_registry/{client_ip}.txt'
    file = open(file_path, 'a')

    message = connection_socket.recv(2048).decode()
    file.write(f'{client_ip}: {message}\n')

    # The peer wants to register to the application
    if message.startswith('REGISTER'):
        message = message.split()

        ui_lock.acquire()
        # Check if the username is taken
        if message[1] in user_information.keys():
            connection_socket.send('100 USERNAME_TAKEN'.encode())
            print(f'User data: {user_information}')
            file.write('REGISTRY: 100 USERNAME_TAKEN\n')
        else:
            user_information[message[1]] = message[2]
            connection_socket.send('101 REGISTER_SUCCESSFUL'.encode())
            print(f'User data: {user_information}')
            file.write('REGISTRY: 101 REGISTER_SUCCESSFUL\n')
        ui_lock.release()

    # The peer wants to log in
    elif message.startswith('LOGIN'):
        message = message.split()

        ui_lock.acquire()
        ou_lock.acquire()
        if message[1] not in user_information.keys():       # Username is not registered
            connection_socket.send('102 USER_NOT_FOUND'.encode())
            print(f'Online users: {online_users}')
            file.write('REGISTRY: 102 USER_NOT_FOUND\n')
        else:
            if message[2] != user_information[message[1]]:  # Wrong password
                connection_socket.send('103 WRONG_PASSWORD'.encode())
                print(f'Online users: {online_users}')
                file.write('REGISTRY: 103 WRONG_PASSWORD\n')
            else:
                if message[1] in online_users.keys():       # User is already logged in
                    connection_socket.send('104 ALREADY_LOGGED'.encode())
                    print(f'Online users: {online_users}')
                    file.write('REGISTRY: 104 ALREADY_LOGGED\n')
                else:                                       # Login successful
                    online_users[message[1]] = client_ip
                    connection_socket.send('105 LOGIN_SUCCESSFUL'.encode())
                    print(f'Online users: {online_users}')
                    file.write('REGISTRY: 105 LOGIN_SUCCESSFUL\n')

        ui_lock.release()
        ou_lock.release()

    # The peer wants to log out
    elif message == 'LOGOUT':
        ou_lock.acquire()
        is_found = False
        for username, ip in online_users.items():
            if ip == client_ip:                            # Device is logged, make it log out
                del online_users[username]
                is_found = True
                connection_socket.send('106 LOGOUT_SUCCESSFUL'.encode())
                print(f'Online users: {online_users}')
                file.write('REGISTRY: 106 LOGOUT_SUCCESSFUL\n')
                break

        if not is_found:                                  # Device couldn't have been found among online users
            connection_socket.send('107 LOGOUT_FAILED'.encode())
            print(f'Online users: {online_users}')
            file.write('REGISTRY: 107 LOGOUT_FAILED\n')

        ou_lock.release()

    # The peer wants to contact with another peer
    elif message.startswith('SEARCH'):
        message = message.split()

        ui_lock.acquire()
        ou_lock.acquire()
        if message[1] not in user_information.keys():    # The user with given username couldn't have been found
            connection_socket.send('102 USER_NOT_FOUND'.encode())
            file.write('REGISTRY: 102 USER_NOT_FOUND\n')
        else:
            if message[1] not in online_users.keys():   # The user with given username is offline
                connection_socket.send('108 USER_OFFLINE'.encode())
                file.write('REGISTRY: 108 USER_OFFLINE\n')
            else:                                       # User has been found. Send the ip of the user to the peer
                connection_socket.send(f'109 SEARCH_SUCCESSFUL {online_users[message[1]]}'.encode())
                file.write(f'REGISTRY: 109 SEARCH_SUCCESSFUL {online_users[message[1]]}\n')

        ui_lock.release()
        ou_lock.release()

    # Peer wants to close the application
    elif message == 'EXIT':
        connection_socket.send('113 EXIT_CONFIRMED'.encode())
        file.write('REGISTRY: 113 EXIT_CONFIRMED\n')
        closing_socket = socket(AF_INET, SOCK_STREAM)
        closing_socket.connect((client_ip, peer_server_port))
        closing_socket.send('EXIT'.encode())
        file.write('REGISTRY: EXIT\n')
        file.write('---END OF SESSION---\n\n')
        closing_socket.close()

    connection_socket.close()
    file.close()


if __name__ == '__main__':
    main()
