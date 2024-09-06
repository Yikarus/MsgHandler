#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <fcntl.h>
#include <sys/epoll.h>
#include <errno.h>
#include <termios.h>
#include <string>
#include <unordered_map>
#include <functional>

#define MAX_EVENTS 10
#define BUFFER_SIZE 256
#define BAUDRATE B9600
#define PORTS (3) // 假设有三个串口设备

using namespace std;


class ComDev{
public:
    ComDev() : fd(-1), devkind(UnKnown), FromPort(-1), ToPort(-1),
               callback(std::bind(&ComDev::initCallBack, this, std::placeholders::_1)) {}
    int fd; // handler
    enum DevKind{
        UnKnown,
        Gripper = 0x01, // 爪子
        Base = 0x3E, // 基座
        Lazer = 0x28, // 激光
        Transit, // 转发
        Screw = 0x62, // 丝杆
        ValidNum = Screw
    };
    DevKind devkind;
    int FromPort;
    int ToPort;
    string name;
    typedef std::function<void(const char*)> Callback;
    Callback callback;
    void initCallBack(const char* buf) {
        // Msg Handling
        // Future would make bug like Size Func content ...
        // Now it's raw data, first byte would be the dev num
        switch(buf[0]){
            // Now lazer and Gripper don't have feedback.
            case DevKind::Lazer:
            case DevKind::Gripper:
            case DevKind::Base:
                devkind = DevKind::Base;
                callback = std::bind(&ComDev::baseCallBack, this, std::placeholders::_1);
                break;
            case DevKind::Screw:
                devkind = DevKind::Screw;
                callback = std::bind(&ComDev::screwCallBack, this, std::placeholders::_1);
                break;
            default:
                devkind = DevKind::Transit;
                callback = std::bind(&ComDev::transitCallBack, this, std::placeholders::_1);
                break;
        }
    }
    void baseCallBack(const char* buf) {
        write(ToPort, buf, strlen(buf));
    }
    void screwCallBack(const char* buf) {
        write(ToPort, buf, strlen(buf));
    }

    void transitCallBack(const char* buf) {
        write(ToPort, buf, strlen(buf));
    }
};

unordered_map<int, ComDev*> fd2Dev;

char BaseRotorPosRead[] = {0x3e, 0x22, 0x22, 0x33, 0x22};
char ScrewRotorPosRead[] = {0x3e, 0x22, 0x22, 0x33, 0x22};
void sendInitMsg(){
    // This is to send msg and receive
    // send all msgs to the dev
    int InitNum = 0;
    for(auto [fd, dev] : fd2Dev){
        if(dev->devkind == ComDev::DevKind::UnKnown) {
            write(fd, BaseRotorPosRead, size(BaseRotorPosRead));
            // TODO: check if need nop
            write(fd, ScrewRotorPosRead, size(ScrewRotorPosRead));
        } else if(dev->devkind != ComDev::DevKind::Transit) {
            InitNum++;
        }
    }
    if(InitNum == PORTS - 2) {
        for(auto [fd, dev] : fd2Dev){
            if(dev->devkind == ComDev::DevKind::UnKnown) {
                dev->devkind = ComDev::DevKind::Gripper;
                // dev->callback = std::bind(&ComDev::baseCallBack, this, std::placeholders::_1);;
            }
        }
    }
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
        const ComDev& dev = *fd2Dev[fd];
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
            dev.callback(buffer);
        }

        if (events[i].events & EPOLLOUT) {
            // 这里可以添加发送数据的逻辑
            // write(fd, "响应数据", strlen("响应数据"));
        }
    }
}

int main() {
    int epoll_fd;
    struct epoll_event ev;
    char buffer[BUFFER_SIZE];
    
    // 创建epoll实例
    epoll_fd = epoll_create1(0);
    if (epoll_fd == -1) {
        perror("epoll_create1");
        return -1;
    }

    // 初始化串口设备
    ComDev devs[PORTS];
    devs[0].name = "/dev/tty1";
    devs[1].name = "/dev/tty2";
    devs[2].name = "/dev/tty3";
    for (int i = 0; i < PORTS; ++i) {
        devs[i].fd = setup_serial_port(devs[i].name.c_str(), BAUDRATE);
        if (devs[i].fd == -1) {
            fprintf(stderr, "无法初始化串口设备 %s\n", devs[i].name.c_str());
            exit(1);
        }

        // 注册事件
        ev.events = EPOLLIN;
        ev.data.fd = devs[i].fd;
        fd2Dev[devs[i].fd] = &devs[i];
        ev.data.ptr = (void *)devs[i].name.c_str(); // 存储端口号，方便识别
        if (epoll_ctl(epoll_fd, EPOLL_CTL_ADD, devs[i].fd, &ev) == -1) {
            perror("epoll_ctl: add");
            fprintf(stderr, "无法添加串口设备 %s 到 epoll\n", devs[i].name.c_str());
            close(devs[i].fd);
            continue;
        }
    }

    sendInitMsg();
    while (1) {
        handle_events(epoll_fd, buffer);
    }

    // 关闭所有串口设备
    for (int i = 0; i < PORTS; ++i) {
        if (devs[i].fd != -1) {
            close(devs[i].fd);
        }
    }

    close(epoll_fd);

    return 0;
}