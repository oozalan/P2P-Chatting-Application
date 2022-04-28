import msvcrt
import os.path
import sys
from socket import *
from time import *
from threading import *

server_ip = '192.168.1.158'       # This needs to be changed if the server changes
server_port = 12345
peer_server_port = 23456
username = ''
is_busy = False
is_chat_over = False
is_app_running = True
is_new_message_arrived = False
file_lock = Lock()

status_codes = {
    '100': 'This username is already being used. Please try another.',
    '101': 'You have registered successfully.',
    '102': "An account couldn't has been found with the given username.",
    '103': 'Password is invalid. Please try again.',
    '104': 'You are already logged in.',
    '105': 'You have logged in successfully.',
    '106': 'You have logged out successfully.',
    '107': 'You are not online.',
    '108': 'User with the given username is offline.',
    '110': 'Connection has been established with the user. Starting chat...',
    '111': 'The user has rejected your chat request.',
    '112': 'The user is chatting with another user.'
}


def main():
    if not os.path.isdir('log_peer'):
        os.mkdir('log_peer')

    # Server thread of the peer
    thread = Thread(target=peer_server_side)
    thread.start()
    main_menu()


# This function displays the main menu and does necessary jobs according to user's input
def main_menu():
    global username
    global is_app_running

    print('---MAIN MENU---')
    print('Please select one of the options:')
    print('[1] Register')
    print('[2] Login')
    print('[3] Exit')

    choice = input('Your choice: ')
    if choice == '1':
        user_data = input('Enter a username and password: ')
        user_data = user_data.split()
        to_server('REGISTER', user_data[0], user_data[1])
        print_stars()
        main_menu()
    elif choice == '2':
        user_data = input('Enter your username and password: ')
        user_data = user_data.split()
        status_code = to_server('LOGIN', user_data[0], user_data[1])
        print_stars()
        if status_code == '105':
            username = user_data[0]
            after_login()
        else:
            main_menu()
    else:
        is_app_running = False
        # Peer sends this message in order to close the server thread of itself
        to_server('EXIT')
        exit()


# This function displays after-login menu and does necessary jobs according to user's input
def after_login():
    global username

    print(f'Hello, {username}')
    print('Please select one of the options:')
    print('[1] Send chat request to someone')
    print('[2] Logout')
    print('[3] Answer call')

    choice = input('Your choice: ')
    if choice == '1':
        entered_username = input('Enter the username of the person you want to chat: ')
        print('Waiting for response...')
        return_value = to_server('SEARCH', entered_username)
        if return_value[0] != '109':
            print_stars()
            after_login()
        else:
            start_chat(return_value[1])
    elif choice == '2':
        to_server('LOGOUT')
        username = ''
        print_stars()
        main_menu()
    elif choice == '3':
        print('Do you want to accept the chat request? (y/n):')


# This function sends a message to the registry
def to_server(*args):
    client_socket = socket(AF_INET, SOCK_STREAM)
    client_socket.connect((server_ip, server_port))

    if args[0] == 'REGISTER' or args[0] == 'LOGIN':
        client_socket.send(f'{args[0]} {args[1]} {args[2]}'.encode())
    elif args[0] == 'LOGOUT' or args[0] == 'EXIT':
        client_socket.send(f'{args[0]}'.encode())
    elif args[0] == 'SEARCH':
        client_socket.send(f'{args[0]} {args[1]}'.encode())

    server_response = client_socket.recv(2048).decode().split()
    client_socket.close()

    if server_response[0] == '113':  # Peer is closing the application, no need to return anything
        return
    elif server_response[0] != '109':
        print(status_codes[server_response[0]])
        sleep(1)
        return server_response[0]
    else:
        return server_response[0], server_response[2]


# This function sends a chat request to another user
def start_chat(peer_server_ip):
    global is_busy
    file_path = f'log_peer/{peer_server_ip}.txt'

    peer_client_socket = socket(AF_INET, SOCK_STREAM)
    peer_client_socket.connect((peer_server_ip, peer_server_port))
    peer_client_socket.send(f'CHAT {username}'.encode())
    write_to_file(file_path, f'YOU: CHAT {username}')

    peer_server_response = peer_client_socket.recv(2048).decode()
    write_to_file(file_path, f'{peer_server_ip}: {peer_server_response}')
    peer_client_socket.close()

    peer_server_response = peer_server_response.split()
    print(status_codes[peer_server_response[0]])
    sleep(1)
    print_stars()

    if peer_server_response[0] == '110':
        is_busy = True
        print('<----------CHAT---------->')
        thread = Thread(target=send_msg_to_peer, args=(peer_server_ip,))
        thread.start()
    else:
        write_to_file(file_path, '---END OF SESSION---\n')
        after_login()


# This function sends message to another user
def send_msg_to_peer(peer_server_ip):
    global is_busy
    global is_chat_over
    global is_new_message_arrived
    file_path = f'log_peer/{peer_server_ip}.txt'

    # Function will exit this loop once the chat finishes, by checking the variable named 'is_chat_over'
    while True:
        message = []
        # Function will exit this loop once the user types something and presses enter key,
        # function will understand whether if the enter key is pressed or not at line 183
        while True:
            if is_chat_over:
                break

            # This is for preventing the overlapping of incoming message and the message
            # the user is currently typing
            if is_new_message_arrived:
                sys.stdout.write(''.join(message))
                is_new_message_arrived = False

            # Read the input letters one by one, store them in the list named 'message'
            if msvcrt.kbhit():
                key_stroke = msvcrt.getche()
                key_stroke = key_stroke.decode('iso-8859-9')
                if key_stroke == '\r':
                    print()
                    break
                # If backspace is pressed; first go the beginning of the line by using
                # the \r character, and then print spaces with the amount equal to the
                # length of the message to remove them from screen, and then remove the
                # last element from the list, finally print the previously typed input
                # back
                elif key_stroke == '\b':
                    if len(message) != 0:
                        for i in range(len(message)):
                            if i == 0:
                                sys.stdout.write('\r ')
                            else:
                                sys.stdout.write(' ')
                        message.pop()
                        current_line = ''.join(message)
                        sys.stdout.write(f'\r{current_line}')
                else:
                    message.append(key_stroke)

        if is_chat_over:
            is_chat_over = False
            break

        message = ''.join(message)
        peer_client_socket = socket(AF_INET, SOCK_STREAM)
        peer_client_socket.connect((peer_server_ip, peer_server_port))
        peer_client_socket.send(f'MESSAGE {username} {message}'.encode())
        write_to_file(file_path, f'YOU: MESSAGE {username} {message}')
        peer_client_socket.close()

        if message == '!quit':
            write_to_file(file_path, '---END OF SESSION---\n')
            print('[APP] You have left the chat. Returning to login menu...')
            is_busy = False
            sleep(1)
            print_stars()
            thread = Thread(target=after_login)
            thread.start()
            break


# This function listens to a TCP port and create a thread for each peer
def peer_server_side():
    global is_app_running

    # noinspection DuplicatedCode
    peer_server_socket = socket(AF_INET, SOCK_STREAM)
    peer_server_socket.bind(('', peer_server_port))
    peer_server_socket.listen()
    while is_app_running:
        connection_socket, peer_client_address = peer_server_socket.accept()
        thread = Thread(target=handle_peer, args=(connection_socket, peer_client_address[0]))
        thread.start()


# This function handles incoming messages from another users, and 1 exit message from registry
def handle_peer(connection_socket, peer_client_ip):
    global is_busy
    global is_chat_over
    global is_new_message_arrived

    file_path = f'log_peer/{peer_client_ip}.txt'
    message = connection_socket.recv(2048).decode()

    if message != 'EXIT':
        write_to_file(file_path, f'{peer_client_ip}: {message}')

    message = message.split(maxsplit=2)
    if message[0] == 'CHAT':
        if is_busy:
            connection_socket.send('112 BUSY'.encode())
            write_to_file(file_path, 'YOU: 112 BUSY')
        else:
            # This print statement say 'type and enter 3' but the if statement above checks
            # if it is 'y' or 'n'. The reason of this is, when a chat request arrives, peer
            # that receives the chat request has one input function waiting for him/her to type
            # something (input function at line 87). To bypass this input function, the program
            # prompts the user to enter 3
            print(f'\rIncoming chat request from user {message[1]} -> Type and enter 3: ')
            answer = input()
            if answer == 'y':
                connection_socket.send('110 CHAT_REQUEST_ACCEPTED'.encode())
                write_to_file(file_path, 'YOU: 110 CHAT_REQUEST_ACCEPTED')
                is_busy = True
                print('Starting chat...')
                sleep(1)
                print_stars()
                print('<----------CHAT---------->')
                thread1 = Thread(target=send_msg_to_peer, args=(peer_client_ip,))
                thread1.start()
            else:
                connection_socket.send('111 CHAT_REQUEST_REJECTED'.encode())
                write_to_file(file_path, 'YOU: 111 CHAT_REQUEST_REJECTED')
                print('You have rejected the request. Redirecting...')
                sleep(1)
                print_stars()
                after_login()
    elif message[0] == 'MESSAGE':
        if message[2] != '!quit':
            print(f'\r{message[1]}: {message[2]}')
            is_new_message_arrived = True
        else:
            write_to_file(file_path, '---END OF SESSION---\n')
            print('[APP] The user have left the chat. Returning to login menu...')
            is_chat_over = True
            is_busy = False
            sleep(1)
            print_stars()
            thread2 = Thread(target=after_login)
            thread2.start()
    # This is the only message coming from the registry. It is sent to the peer after peer executes
    # the code at line 75, to close the server thread of the peer and make it close the application completely
    elif message[0] == 'EXIT':
        print('Closing the application...')
        sleep(1)

    connection_socket.close()


def print_stars():
    for _ in range(3):
        print('*')


def write_to_file(path, sentence):
    file_lock.acquire()
    file = open(path, 'a')
    file.write(f'{sentence}\n')
    file.close()
    file_lock.release()


if __name__ == '__main__':
    main()
