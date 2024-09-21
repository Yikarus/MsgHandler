# ******************************************************************************
#  Copyright (c) 2023 Orbbec 3D Technology, Inc
#  
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.  
#  You may obtain a copy of the License at
#  
#      http:# www.apache.org/licenses/LICENSE-2.0
#  
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
# ******************************************************************************
import time

import cv2
import numpy as np

from pyorbbecsdk import Config
from pyorbbecsdk import OBSensorType
from pyorbbecsdk import Pipeline
from pyorbbecsdk import OBSensorType, OBFormat
import socket
import time
from PIL import Image
import io
import struct
from utils import frame_to_bgr_image

ESC_KEY = 27
PRINT_INTERVAL = 1  # seconds
MIN_DEPTH = 20  # 20mm
MAX_DEPTH = 10000  # 10000mm
TIME_WAIT = 0.1 # second

def send_image(sock, color_image, depth_image):
    # print("image.shape:", image.shape)
    # height, width, _ = image.shape
    # sock.sendall(struct.pack('!II', height, width))  # 发送图像大小
    # sock.sendall(image)  # 发送图像数据
    print("color.shape:", color_image.shape)
    print("depth.shape:", depth_image.shape)
    _, color_buffer = cv2.imencode('.jpg', color_image)
    # _, depth_buffer = cv2.imencode('.jpg', depth_image)
    height, width = depth_image.shape
    depth_size = height * width * 2
    print("send color len:", len(color_buffer.tobytes()), " depth:", depth_size)
    size_data = struct.pack('!II', len(color_buffer.tobytes()), depth_size)
    sock.sendall(size_data)
    sock.sendall(color_buffer.tobytes())  # 发送图像数据
    sock.sendall(depth_image)
    print("color.jpg:", len(color_buffer.tobytes()))
    print("depth.jpg:", len(depth_image))

class TemporalFilter:
    def __init__(self, alpha):
        self.alpha = alpha
        self.previous_frame = None

    def process(self, frame):
        if self.previous_frame is None:
            result = frame
        else:
            result = cv2.addWeighted(frame, self.alpha, self.previous_frame, 1 - self.alpha, 0)
        self.previous_frame = result
        return result


def main():
    config = Config()
    pipeline = Pipeline()
    temporal_filter = TemporalFilter(alpha=0.5)
    try:
        depth_profile_list = pipeline.get_stream_profile_list(OBSensorType.DEPTH_SENSOR)
        color_profile_list = pipeline.get_stream_profile_list(OBSensorType.COLOR_SENSOR)
        assert depth_profile_list is not None and color_profile_list is not None
        depth_profile = depth_profile_list.get_default_video_stream_profile()
        color_profile = color_profile_list.get_video_stream_profile(848, 0, OBFormat.RGB, 30)
        # color_profile = color_profile_list.get_default_video_stream_profile()
        assert depth_profile is not None and color_profile is not None
        print("depth profile: ", depth_profile_list)
        print("color profile: ", color_profile_list)
        config.enable_stream(depth_profile)
        config.enable_stream(color_profile)
    except Exception as e:
        print(e)
        return

    host = '0.0.0.0'  # 监听所有可用的网络接口
    port = 12345  # 初始化端口号

    try:
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.bind((host, port))
        server_socket.listen(5)
        print(f"Server listening on port {port}")
    except Exception as e:
        print(f"An bind error occurred: {e}")
        exit(1)
    pipeline.start(config)
    last_print_time = time.time()
    while True:
        conn, address = server_socket.accept()
        print(f"Got connection from {address}")
        while True:
            try:
                frames = pipeline.wait_for_frames(100)
                if frames is None:
                    continue
                depth_frame = frames.get_depth_frame()
                if depth_frame is None:
                    continue
                width = depth_frame.get_width()
                height = depth_frame.get_height()
                scale = depth_frame.get_depth_scale()

                depth_data = np.frombuffer(depth_frame.get_data(), dtype=np.uint16)
                depth_data = depth_data.reshape((height, width))

                depth_data = depth_data.astype(np.float32) * scale
                depth_data = np.where((depth_data > MIN_DEPTH) & (depth_data < MAX_DEPTH), depth_data, 0)
                depth_data = depth_data.astype(np.uint16)
                # Apply temporal filtering
                depth_data = temporal_filter.process(depth_data)
                center_y = int(height / 2)
                center_x = int(width / 2)
                center_distance = depth_data[center_y, center_x]

                current_time = time.time()
                if current_time - last_print_time >= PRINT_INTERVAL:
                    print("center distance: ", center_distance)
                    last_print_time = current_time

                # depth_image = cv2.normalize(depth_data, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)
                # depth_image = cv2.applyColorMap(depth_image, cv2.COLORMAP_JET)

                # get color frame
                color_frame = frames.get_color_frame()
                if color_frame is None:
                    continue
                # covert to RGB format
                color_image = frame_to_bgr_image(color_frame)
                if color_image is None:
                    print("failed to convert frame to image")
                    continue
                send_image(conn, color_image, depth_data)
                time.sleep(TIME_WAIT)
            except BrokenPipeError:
                print("Client disconnected")
                conn.close()
                break
            except Exception as e:
                print(f"An error occurred: {e}")
                conn.close()
                break
            except KeyboardInterrupt as e:
                conn.close()
                break
    pipeline.stop()
    server_socket.close()

if __name__ == "__main__":
    main()
