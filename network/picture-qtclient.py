import sys
import socket
import io
from PIL import Image
from PyQt6.QtWidgets import QApplication, QLabel, QWidget
from PyQt6.QtGui import QPixmap, QImage
from PyQt6.QtCore import Qt

class ImageWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.image_label = QLabel(self)
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.resize(1920, 1080)  # 假设图像大小为 1920x1080
        
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Image Viewer')
        self.resize(1920, 1080)
        self.show()

    def update_image(self, image_data):
        image = Image.open(io.BytesIO(image_data))
        # 创建 QImage 时需要指定字节步长
        qimage = QImage(
            image.tobytes(),
            image.width,
            image.height,
            image.width * 3,
            QImage.Format.Format_RGB888
        )
        # 交换颜色通道以适应 QImage 的 RGB 格式
        qimage = qimage.rgbSwapped()
        pixmap = QPixmap.fromImage(qimage)
        self.image_label.setPixmap(pixmap)

def receive_image(sock):
    image_size = int.from_bytes(sock.recv(4), byteorder='big')  # 接收图像大小
    image_data = b''
    while len(image_data) < image_size:
        packet = sock.recv(image_size - len(image_data))
        if not packet:
            return None
        image_data += packet
    return image_data

def client_program():
    host = '127.0.0.1'  # 服务器的 IP 地址
    port = 12345  # 端口号必须与服务器相同
    
    app = QApplication(sys.argv)
    widget = ImageWidget()

    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((host, port))

    while True:
        image_data = receive_image(client_socket)
        if image_data is not None:
            widget.update_image(image_data)
            app.processEvents()  # 更新GUI

    client_socket.close()
    sys.exit(app.exec())

if __name__ == '__main__':
    client_program()