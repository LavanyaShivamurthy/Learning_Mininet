import socket
import time
import sys

def send_sensor_data(destination_ip, port=5555):
    try:
        # Create UDP socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        # Enable broadcasting (if needed)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        
        # Sensor data payload
        sensor_data_list = [
            "Temperature:25C",
            "Humidity:60%",
            "Pressure:1013hPa",
            "CO2:400ppm"
        ]
        
        print(f"Sending UDP data to {destination_ip}:{port}")
        
        # Continuous sending
        while True:
            for data in sensor_data_list:
                # Send sensor data
                sock.sendto(data.encode(), (destination_ip, port))
                print(f"Sent to {destination_ip}:{port} - {data}")
                
                # Small delay between messages
                time.sleep(1)
    
    except Exception as e:
        print(f"Error sending sensor data: {e}")
    finally:
        sock.close()

if __name__ == "__main__":
    # Check if destination IP is provided
    if len(sys.argv) != 2:
        print("Usage: python sensor_script.py <destination_ip>")
        sys.exit(1)
    
    destination_ip = sys.argv[1]
    send_sensor_data(destination_ip)
