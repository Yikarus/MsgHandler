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
import cv2

from pyorbbecsdk import Config
from pyorbbecsdk import OBError
from pyorbbecsdk import OBSensorType, OBFormat
from pyorbbecsdk import Pipeline, FrameSet
from pyorbbecsdk import VideoStreamProfile
from utils import frame_to_bgr_image

import socket
import time
from PIL import Image
import io


ESC_KEY = 27

def send_image(sock, image):
    print("lenffff:", image.shape)
    sock.sendall(len(image).to_bytes(4, byteorder='big'))  # 发送图像大小
    sock.sendall(image)  # 发送图像数据

def main():
    config = Config()
    pipeline = Pipeline()
    try:
        profile_list = pipeline.get_stream_profile_list(OBSensorType.COLOR_SENSOR)
        try:
            color_profile: VideoStreamProfile = profile_list.get_video_stream_profile(640, 0, OBFormat.RGB, 30)
        except OBError as e:
            print(e)
            color_profile = profile_list.get_default_video_stream_profile()
            print("color profile: ", color_profile)
        config.enable_stream(color_profile)
    except Exception as e:
        print(e)
        return
    pipeline.start(config)
    host = '0.0.0.0'  # 监听所有可用的网络接口
    port = 12345  # 初始化端口号

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((host, port))
    server_socket.listen(5)
    print(f"Server listening on port {port}")

    try:
        while True:
            conn, address = server_socket.accept()
            print(f"Got connection from {address}")

            try:
                while True:
                    frames: FrameSet = pipeline.wait_for_frames(100)
                    if frames is None:
                        continue
                    color_frame = frames.get_color_frame()
                    if color_frame is None:
                        continue
                    # covert to RGB format
                    color_image = frame_to_bgr_image(color_frame)
                    if color_image is None:
                        print("failed to convert frame to image")
                        continue
                    send_image(conn, color_image)
                    time.sleep(0.1)  # 等待1秒
            except BrokenPipeError:
                print("Client disconnected")
            except Exception as e:
                print(f"An error occurred: {e}")
            except KeyboardInterrupt:
                conn.close()
                break
            finally:
                conn.close()
    except KeyboardInterrupt:
        print("Server shutting down.")
    finally:
        server_socket.close()
    pipeline.stop()


if __name__ == "__main__":
    main()
