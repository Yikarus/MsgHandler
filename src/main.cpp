#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <fcntl.h>
#include <sys/epoll.h>
#include <errno.h>
#include <termios.h>

#define MAX_EVENTS 10
#define BUFFER_SIZE 256
#define BAUDRATE B9600
#define PORTS (3) // 假设有三个串口设备




class ComDev{
public:
    int fd; // handler
    enum {
        Gripper, // 爪子
        Base, // 基座
        Lazer, // 激光
        Transit, // 转发
        Screw, // 丝杆
        ValidNum = Screw
    } DevKind;
    DevKind devkind;
    int FromPort;
    int ToPort;
    typedef void (*Callback)(const char*);
    Callback InitFunc;
    Callback callback;
};

void InitCallBack(const char* msg){
    // This is to send msg and receive
    
}
// 初始化串口设备
int setup_serial_port(const char *port, speed_t baudrate) {
    int fd;
    struct termios options;

    // 打开串口设备
    if ((fd = open(port, O_RDWR | O_NOCTTY | O_SYNC)) == -1) {
        perror("无法打开串口");
        return -1;
    }

    // 初始化termios结构
    memset(&options, 0, sizeof(options));

    // 设置波特率
    cfsetispeed(&options, baudrate);
    cfsetospeed(&options, baudrate);

    // 设置数据位、停止位和校验位
    options.c_cflag |= (CLOCAL | CREAD);
    options.c_cflag &= ~CSIZE;     // Clear the character size flags
    options.c_cflag |= CS8;        // 8-bit characters
    options.c_cflag &= ~PARENB;    // Disable parity checking
    options.c_cflag &= ~CSTOPB;    // 1 stop bit
    options.c_cflag &= ~CRTSCTS;   // Disable RTS/CTS hardware flow control

    // 设置接收和发送缓冲区控制
    options.c_iflag &= ~(IXON | IXOFF | IXANY); // Disable software flow control
    options.c_iflag &= ~(IGNBRK|BRKINT|PARMRK|ISTRIP|INLCR|IGNCR|ICRNL); // Disable any special handling of received bytes
    options.c_oflag &= ~OPOST;      // Prevent special interpretation of output bytes (e.g., newline chars)
    options.c_oflag &= ~(ONLCR);    // Prevent conversion of newline to carriage return/line feed

    // Set the buffer size for the input and output buffers
    options.c_cc[VMIN]  = 1; // Wait for at least one character before returning
    options.c_cc[VTIME] = 5; // Wait up to half a second (500ms)

    // 应用设置
    if (tcsetattr(fd, TCSANOW, &options) != 0) {
        perror("tcsetattr");
        fprintf(stderr, "Error setting attributes: %s (%d)\n", strerror(errno), errno);
        close(fd);
        return -1;
    }

    return fd;
}

// 处理事件
void handle_events(int epoll_fd, char *buffer) {
    struct epoll_event events[MAX_EVENTS];
    int num_events, i;
    char *port_name;

    num_events = epoll_wait(epoll_fd, events, MAX_EVENTS, -1);
    if (num_events == -1) {
        perror("epoll_wait");
        return;
    }

    for (i = 0; i < num_events; i++) {
        int fd = events[i].data.fd;

        if (events[i].events & EPOLLIN) {
            ssize_t nread = read(fd, buffer, BUFFER_SIZE - 1);
            if (nread <= 0) {
                if (nread == -1 && errno != EAGAIN) {
                    fprintf(stderr, "读取失败: %s (%d)\n", strerror(errno), errno);
                }
                continue;
            }
            buffer[nread] = '\0';
            port_name = (strstr((char*)events[i].data.ptr, "/dev/") + 5);
            printf("从 %s 接收到: %s\n", port_name, buffer);
        }

        if (events[i].events & EPOLLOUT) {
            // 这里可以添加发送数据的逻辑
            // write(fd, "响应数据", strlen("响应数据"));
        }
    }
}

int main() {
    int epoll_fd, serial_fds[PORTS];
    struct epoll_event ev;
    char buffer[BUFFER_SIZE];

    // 创建epoll实例
    epoll_fd = epoll_create1(0);
    if (epoll_fd == -1) {
        perror("epoll_create1");
        return -1;
    }

    // 初始化串口设备
    const char *ports[] = {"/dev/ttyS0", "/dev/ttyS1", "/dev/ttyS2"};
    for (int i = 0; i < PORTS; ++i) {
        serial_fds[i] = setup_serial_port(ports[i], BAUDRATE);
        if (serial_fds[i] == -1) {
            fprintf(stderr, "无法初始化串口设备 %s\n", ports[i]);
            continue;
        }

        // 注册事件
        ev.events = EPOLLIN | EPOLLOUT;
        ev.data.fd = serial_fds[i];
        ev.data.ptr = (void *)ports[i]; // 存储端口号，方便识别
        if (epoll_ctl(epoll_fd, EPOLL_CTL_ADD, serial_fds[i], &ev) == -1) {
            perror("epoll_ctl: add");
            fprintf(stderr, "无法添加串口设备 %s 到 epoll\n", ports[i]);
            close(serial_fds[i]);
            continue;
        }
    }

    while (1) {
        handle_events(epoll_fd, buffer);
    }

    // 关闭所有串口设备
    for (int i = 0; i < PORTS; ++i) {
        if (serial_fds[i] != -1) {
            close(serial_fds[i]);
        }
    }

    close(epoll_fd);

    return 0;
}