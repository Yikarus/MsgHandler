import socket
import cv2
import numpy as np
import struct
from pyorbbecsdk import (Pipeline, Context, Config, OBSensorType,
                         OBFormat, OBError)
from utils import frame_to_bgr_image  # 确保你有一个 utils 模块，里面定义了 frame_to_bgr_image 函数

def send_video_stream(sock, pipeline):
    while True:
        frames = pipeline.wait_for_frames(100)
        if not frames:
            continue

        color_frame = frames.get_color_frame()
        if color_frame:
            if color_frame.get_format() in [OBFormat.H265, OBFormat.H264]:
                color_format = 'h265' if color_frame.get_format() == OBFormat.H265 else 'h264'
                color_image = decode_h265_frame(color_frame, color_format)
            else:
                color_image = frame_to_bgr_image(color_frame)

            if color_image is not None:
                # 将图像编码为 JPEG 格式
                _, encoded_image = cv2.imencode('.jpg', color_image)
                data = encoded_image.tobytes()
                message_size = struct.pack("L", len(data))
                sock.sendall(message_size + data)
                time.sleep(0.03)  # 控制帧率

def get_stream_profile(pipeline, sensor_type, width, height, fmt, fps):
    profile_list = pipeline.get_stream_profile_list(sensor_type)
    try:
        profile = profile_list.get_video_stream_profile(width, height, fmt, fps)
    except OBError:
        profile = profile_list.get_default_video_stream_profile()
    return profile

def decode_h265_frame(color_frame, color_format='hevc'):
    # This function is only supported on Linux.
    # and requires ffmpeg to be installed.
    if color_format == 'h265':
        color_format = 'hevc'
    elif color_format == 'h264':
        color_format = 'h264'

    cmd_in = [
        'ffmpeg',
        '-f', color_format,
        '-i', 'pipe:',
        '-f', 'rawvideo',
        '-pix_fmt', 'bgr24',
        'pipe:'
    ]

    byte_data = color_frame.get_data().tobytes()

    try:
        proc = subprocess.run(cmd_in, input=byte_data, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        decoded_frame = np.frombuffer(proc.stdout, dtype=np.uint8).reshape(color_frame.get_height(), color_frame.get_width(), 3)
        return decoded_frame
    except subprocess.CalledProcessError as e:
        print(f"FFmpeg failed with error code {e.returncode}: {e.stderr.decode()}")
        return None

def server_program():
    host = '0.0.0.0'  # 监听所有可用的网络接口
    port = 12345  # 初始化端口号
    
    ctx = Context()
    ip = input("Enter the ip address of the device (default: 192.168.1.10): ") or "192.168.1.10"
    device = ctx.create_net_device(ip, 8090)
    if device is None:
        print("Failed to create net device")
        return

    config = Config()
    pipeline = Pipeline(device)

    # Setup color stream
    color_profile = get_stream_profile(pipeline, OBSensorType.COLOR_SENSOR, 1280, 0, OBFormat.MJPG, 10)
    config.enable_stream(color_profile)

    # Setup depth stream
    depth_profile = get_stream_profile(pipeline, OBSensorType.DEPTH_SENSOR, 640, 0, OBFormat.Y16, 10)
    config.enable_stream(depth_profile)

    pipeline.start(config)

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((host, port))
    server_socket.listen(5)
    print(f"Server listening on port {port}")

    try:
        while True:
            conn, address = server_socket.accept()
            print(f"Got connection from {address}")
            send_video_stream(conn, pipeline)
    except KeyboardInterrupt:
        print("Server shutting down.")
    finally:
        pipeline.stop()
        server_socket.close()

if __name__ == '__main__':
    server_program()