#include <iostream>
#include <libusb-1.0/libusb.h>
#include <unistd.h> // For sleep()

#define VENDOR_ID 0x284e
#define PRODUCT_ID 0x79a1
#define INTERFACE 0
#define CONFIGURATION 1

int main() {
    libusb_device **device_list;
    struct libusb_device *dev;
    struct libusb_context *ctx = nullptr;
    ssize_t cnt;
    int r;

    // Initialize libusb
    r = libusb_init(&ctx);
    if (r < 0) {
        std::cerr << "Failed to initialize libusb: " << r << std::endl;
        return EXIT_FAILURE;
    }

    // Find all devices connected to the system
    cnt = libusb_get_device_list(ctx, &device_list);
    if (cnt < 0) {
        std::cerr << "Failed to get device list: " << cnt << std::endl;
        goto exit;
    }

    // Look for our device in the list
    for (ssize_t i = 0; i < cnt; i++) {
        libusb_device_descriptor desc;
        r = libusb_get_device_descriptor(device_list[i], &desc);
        if (r < 0) {
            std::cerr << "Failed to get descriptor: " << r << std::endl;
            continue;
        }

        if (desc.idVendor == VENDOR_ID && desc.idProduct == PRODUCT_ID) {
            dev = device_list[i];
            break;
        }
    }

    if (!dev) {
        std::cerr << "Device not found." << std::endl;
        goto exit;
    }

    // Open the device
    struct libusb_device_handle *handle;
    r = libusb_open(dev, &handle);
    if (r < 0) {
        std::cerr << "Failed to open device: " << r << std::endl;
        goto exit;
    }

    // Detach kernel driver if necessary
    r = libusb_detach_kernel_driver(handle, INTERFACE);
    if (r == LIBUSB_ERROR_NOT_SUPPORTED) {
        std::cerr << "Kernel driver detachment is not supported." << std::endl;
    } else if (r < 0) {
        std::cerr << "Failed to detach kernel driver: " << r << std::endl;
        goto exit;
    } else if (r == 0) {
        std::cout << "No kernel driver attached." << std::endl;
    }

    // Set configuration
    r = libusb_set_configuration(handle, CONFIGURATION);
    if (r < 0) {
        std::cerr << "Failed to set configuration: " << r << std::endl;
        goto exit;
    }

    // Claim the interface
    r = libusb_claim_interface(handle, INTERFACE);
    if (r < 0) {
        std::cerr << "Failed to claim interface: " << r << std::endl;
        goto exit;
    }

    // Buffer to hold the read data
    unsigned char buffer[64]; // Adjust buffer size as needed
    int transferred;

    // Continuously read from the device
    while (true) {
        r = libusb_interrupt_transfer(
            handle,
            0x81, // Endpoint number
            buffer,
            sizeof(buffer),
            &transferred,
            1000 // Timeout in milliseconds
        );

        if (r == 0) {
            std::cout << "Read " << transferred << " bytes: ";
            for (int i = 0; i < transferred; ++i) {
                std::cout << "0x" << std::hex << static_cast<int>(buffer[i]) << " ";
            }
            std::cout << std::endl;
        } else {
            std::cerr << "Error reading data: " << r << std::endl;
        }

        sleep(1); // Wait for one second
    }

exit:
    if (handle) {
        libusb_release_interface(handle, INTERFACE);
        libusb_attach_kernel_driver(handle, INTERFACE); // Reattach kernel driver
        libusb_close(handle);
    }

    if (device_list) {
        libusb_free_device_list(device_list, 1);
    }

    libusb_exit(ctx);

    return EXIT_SUCCESS;
}