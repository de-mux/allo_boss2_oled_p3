"""
Reference:
- https://github.com/adamyoung600/WRX_HUD/blob/master/Hardware/SH1106/SH1106LCD.py
- https://github.com/olikraus/u8g2/blob/master/csrc/u8x8_d_sh1106_64x32.c
"""
import smbus
import time
from PIL import Image
import traceback
from .SH1106FontLib import capFont
from .Line1SH1106FontLib import Line1
from .SH1106FontLib1 import capFont1
from .SH1106FontLibNumbers import Number1
from .SH1106FontLibNumbers1 import Number2

MAX_BUFFER_LENGTH = 32
WIDTH_PIXELS = 132
COLUMNS = 16
ROWS = 8
PIXELS_PER_ROW = 8
HEIGHT_PIXELS = ROWS * PIXELS_PER_ROW


class SH1106LCD:
    """Interface to the SH1106 LCD that will be displaying the current
    gear selection.  The SH1106 LCD is a 132x64 pixel OLED display.
    Data is displayed on the LCD by alterting the data in the Display
    Data RAM.  The RAM contains a set of bits that correspond to the
    individual pixels of the LCD display. It holds the data in pages
    and columns.  Their are 8 pages, each representing 8 rows (making up
    the 64 bit height).  There are 132 columns in each page.  Each page
    is stored as a set of 132 bytes.  The 8 bits of each byte represent
    one of the 8 rows in that page as shown below. The least significant
    bit (D0) represents the top-most row of the page.  The most
    significant bit (D7) represents the bottom-most row of the page.

    Changes to the Display Data RAM are immediately reflected on the
    actual LCD.  When writing bytes to the RAM, the column position is
    automatically incremented with each byte allowing continuous writing
    to memory. The cursor can also be manually set to any position in RAM.

       | Col 0 | Col 1 | Col 2 | ... | Col 131 |
     ---------------------------------------------------
       |  D0   |  D0   |
     P |  D1   |  D1   |
     A |  D2   |  D2   |
     G |  D3   |  D3   |
     E |  D4   |  D4   |
       |  D5   |  D5   |
     0 |  D6   |  D6   |
       |  D7   |  D7   |
     ----------------------------------------------------
       |  D0   |
     P |  D1   |
     A |  D2   |
     G |  D3   |
     E |  D4   |
       |  D5   |
     1 |  D6   |
       |  D7   |
     ----------------------------------------------------

    """

    COLUMNS = COLUMNS
    ROWS = ROWS

    SET_LOWER_COLUMN_ADDR = 0x00
    SET_HIGHER_COLUMN_ADDR = 0x10
    SET_PUMP_VOLTAGE = 0x30
    SET_DISPLAY_START_LINE = 0x40
    SET_CONTRAST_CONTROL_MODE = 0x81
    SET_SEGMENT_REMAP_RIGHT = 0xA0
    SET_SEGMENT_REMAP_LEFT = 0xA1
    SET_ENTIRE_DISPLAY_OFF = 0xA4
    SET_ENTIRE_DISPLAY_ON = 0xA5
    SET_REVERSE_OFF = 0xA6
    SET_REVERSE_ON = 0xA7
    SET_MULTIPLEX_RATIO_MODE = 0xA8
    SET_DC_DC_CONTROL_MODE = 0xAD
    SET_DISPLAY_OFF = 0xAE
    SET_DISPLAY_ON = 0xAF
    SET_PAGE_ADDR = 0xB0
    SET_COMMON_OUTPUT_SCAN_DIR = 0xC0
    SET_DISPLAY_OFFSET_MODE = 0xD3
    SET_DIVIDE_RATIO_OSC_FREQ_MODE = 0xD5
    SET_PRECHARGE_PERIOD_MODE = 0xD9
    SET_COMMON_PADS_HARDWARE_CONFIG = 0xDA
    SET_VCOM_DESELECT_LEVEL_MODE = 0xDB
    SET_READ_MODIFY_WRITE = 0xE0
    SET_END = 0xEE
    SET_NOP = 0xE3

    def __init__(self):
        # Default i2c bus
        self.bus = smbus.SMBus(1)
        self.OLED_Address = 0x3C
        self.OLED_Command_Mode = 0x80
        self.OLED_Data_Mode = 0x40

        # Initialize the screen.
        self._display_is_on = False
        self.__initialize()

        # Set up internal image buffer
        self.imageBuffer = {}

        # Import font
        self.font = capFont
        self.font1 = capFont1
        self.fontLine1 = Line1
        self.fontNumber = Number1
        self.fontNumber1 = Number2

    def __initialize(self):
        """Initilizes the LCD.  Values are taken from the SH1106 datasheet."""

        time.sleep(0.25)

        self.__sendCommand(self.SET_DISPLAY_OFF)
        self.__sendCommand(self.SET_COMMON_OUTPUT_SCAN_DIR)

        self.__sendCommand(self.SET_LOWER_COLUMN_ADDR)
        self.__sendCommand(self.SET_HIGHER_COLUMN_ADDR)
        self.__sendCommand(self.SET_DISPLAY_START_LINE)

        self.__sendCommand(self.SET_CONTRAST_CONTROL_MODE)
        self.__sendCommand(0x7F)  # 0-255
        self.__sendCommand(self.SET_SEGMENT_REMAP_LEFT)
        self.__sendCommand(self.SET_REVERSE_OFF)
        self.__sendCommand(self.SET_SEGMENT_REMAP_RIGHT)
        self.__sendCommand(self.SET_PUMP_VOLTAGE | 0x3)  # was 0x3F
        self.__sendCommand(self.SET_ENTIRE_DISPLAY_OFF)
        self.__sendCommand(self.SET_DISPLAY_OFFSET_MODE)
        self.__sendCommand(0x00)  # 0-63
        self.__sendCommand(self.SET_DIVIDE_RATIO_OSC_FREQ_MODE)
        # A3-A0 is clock divide ratio, A7-A4 is oscillator frequency adjustment.
        # 0b0101 (5) is nominal, less is slower, more is faster
        self.__sendCommand(0xF0)
        self.__sendCommand(self.SET_PRECHARGE_PERIOD_MODE)
        # A3-A0 is pre-charge period, default is 2.
        # A7-A4 is dis-charge period, default is 2.
        self.__sendCommand(0x22)
        self.__sendCommand(self.SET_COMMON_PADS_HARDWARE_CONFIG)
        self.__sendCommand(0x12)  # 0x2(sequential) or 0x12 (alternative)
        self.__sendCommand(self.SET_VCOM_DESELECT_LEVEL_MODE)
        # Common pad output voltage, Vcom = (0.430 + A[7:0] X 0.006415) X Vref
        self.__sendCommand(0x20)  # beta = 0.63528
        self.clearScreen()
        self.display_on()

        time.sleep(0.1)

    def display_on(self):
        """Turns on the lighting of the LCD.  Will display whatever
        is in the Display Data Ram. Display Data RAM can be
        altered while the LCD is powered down.
        """
        self.__sendCommand(self.SET_DISPLAY_ON)
        self._display_is_on = True

    def display_off(self):
        """Turns off the lighting of the LCD.  LCD will retain
        whatever is in the Display Data Ram.
        """
        self.__sendCommand(self.SET_DISPLAY_OFF)
        self._display_is_on = False

    def clearRow(self, row):
        """row - The row to blank (0 - 7)

        Writes 0x00 to every address in Display Data Ram
        for a given row.  This will blank the row.
        """
        page = self.SET_PAGE_ADDR + row
        self.__sendCommand(page)
        row_data = [0x00] * WIDTH_PIXELS
        self.sendData(row_data)

    def clearScreen(self, keep_display_off=False):
        """Writes 0x00 to every address in the Display Data Ram
        effectively making the screen completely black.
        Should be called on first connection of the LCD as
        when uninitialized the LCD will display random pixels.
        """
        previous_state = self._display_is_on
        self.display_off()
        for row in range(ROWS):
            self.clearRow(row)
            self.__sendCommand(self.SET_LOWER_COLUMN_ADDR)  # reset column address
            self.__sendCommand(self.SET_HIGHER_COLUMN_ADDR)  # reset column address
        if previous_state and not keep_display_off:
            self.display_on()

    def setCursorPosition(self, row, col):
        """
        row - The row to place the cursor on (0 - 7)
        col - The column to place the cursor on (0 - 31)
        """
        # Set row
        page = self.SET_PAGE_ADDR + row
        self.__sendCommand(page)
        # For some reason, the LCD does not seem to be correctly set up to
        # display on the first two collumn addresses. Therefore increase the
        # column value by 2
        col = col + 2

        # Calculate the command bytes to set the column address
        # Column Address Offset: A7 A6 A5 A4 A3 A2 A1 A0
        # Upper Address Nibble Command: 0 0 0 0 A3 A2 A1 A0
        # Lower Address Nibble Command: 0 0 0 1 A7 A6 A5 A4
        lowerColumnOffsetByte = col & 0x0F
        upperColumnOffsetByte = (col >> 4) + self.SET_HIGHER_COLUMN_ADDR
        # Set column
        self.__sendCommand(upperColumnOffsetByte)  # Upper 4 bits
        self.__sendCommand(lowerColumnOffsetByte)  # Lower 4 bits

    def __sendCommand(self, command):
        """command - Hex data to send to the OLED as a command

        Used to send data to the OLED that should be interpreted as a command,
        and not display data.  Commands are used to control the
        functions/configuration of the OLED.  This method sends the control byte
        with the D/C Bit set LOW to tell the OLED that the next data sent will be
        a command
        """
        retries = 10
        while retries > 0:
            try:
                self.bus.write_byte_data(
                    self.OLED_Address, self.OLED_Command_Mode, command
                )
            except IOError:
                retries -= 1
            else:
                break

    def __sendDataByte(self, dataByte):
        """Sends a single display data byte to the Display Data RAM.

        dataByte - Single byte of data (in hex) to send to the OLED as display data.
        """
        retries = 10
        while retries > 0:
            try:
                self.bus.write_byte_data(
                    self.OLED_Address, self.OLED_Data_Mode, dataByte
                )
            except IOError:
                retries -= 1
            else:
                break

    def sendDataByte(self, dataByte):
        self.__sendDataByte(dataByte)

    def sendData(self, data):
        """Send an array of bytes to the device controller."""
        if len(data) > MAX_BUFFER_LENGTH:
            splitStream = self.__chunks(list(data), MAX_BUFFER_LENGTH)
            for chunk in splitStream:
                self.__sendData(chunk)
        else:
            self.__sendData(data)

    def __sendData(self, data):
        """data - Bytestream to send to the Display Data RAM.
        Must not exceed MAX_BUFFER_LENGTH.
        """
        retries = 10
        while retries > 0:
            try:
                self.bus.write_i2c_block_data(
                    self.OLED_Address, self.OLED_Data_Mode, data
                )
            except IOError:
                retries -= 1
            else:
                break

    def addImage(self, imageID, filename):
        """Processes an image and adds it to the internal buffer.  This pre-processes
        the image before storing it and avoids unnecessary processing each time you
        wish to display it.

            imageID - String used to identify the stored image.
            filename - File to add.  Must be monochrome bit map
        """
        processedImage = self.LCDImage(filename)
        self.imageBuffer[imageID] = processedImage

    def displayBufferedImage(self, imageID, rowOffset, colOffset):
        """Displays an image on the LCD that has already been pre-processed and placed into the
        internal buffer using the addImage method.

            imageID - String identifying the pre-processed image in the internal buffer.
            row - row on which to start the upper left corner of the image (0-7)
            col - column on which to start the upper left corner of the image (0-31)
        """

        try:
            if imageID not in self.imageBuffer.keys():
                raise ValueError(imageID + " not in the pre-processed image buffer.")
            else:
                image = self.imageBuffer.get(imageID)
            self.__displayProcessedImage(image, rowOffset, colOffset)
        except ValueError:
            print("Value Error: ")
            traceback.print_exc()

    def displayImage(self, filename, rowOffset, colOffset):
        processedImage = self.LCDImage(filename)
        self.__displayProcessedImage(processedImage, rowOffset, colOffset)

    def displayStringNumber(self, inString, row, col, wrap=None):
        if wrap is None:
            wrap = False
        displayStringNumber = inString
        # Set the row/column position
        self.setCursorPosition(row, col)
        for c in displayStringNumber:
            # Get the ascii value and then subtract 32 as the font does not
            # have any characters before the 32nd implemented.
            fontIndex = ord(c) - 32
            self.__sendData(self.fontNumber[fontIndex])
            self.__sendDataByte(0x00)
        self.setCursorPosition(row + 1, col)
        for c in displayStringNumber:
            # Get the ascii value and then subtract 32 as the font does not
            # have any characters before the 32nd implemented.
            fontIndex = ord(c) - 32
            self.__sendData(self.fontNumber1[fontIndex])
            self.__sendDataByte(0x00)

    def displayStringLine1(self, inString, row, col, wrap=None):
        if wrap is None:
            wrap = False
        displayStringLine1 = inString
        # Set the row/column position
        self.setCursorPosition(row, col)
        for c in displayStringLine1:
            # Get the ascii value and then subtract 32 as the font does not
            # have any characters before the 32nd implemented.
            fontIndex = ord(c) - 32
            self.__sendData(self.fontLine1[fontIndex])
            self.__sendDataByte(0x00)

    def displayString(self, inString, row, col, wrap=None):
        if wrap is None:
            wrap = False
        # Convert string to all caps as lower case characters are not
        # implemented in the font.
        displayString = inString
        # Set the row/column position
        self.setCursorPosition(row, col)
        for c in displayString:
            # Get the ascii value and then subtract 32 as the font does not
            # have any characters before the 32nd implemented.
            fontIndex = ord(c) - 32
            self.__sendData(self.font[fontIndex])
            self.__sendDataByte(0x00)
        self.setCursorPosition(row + 1, col)
        for c in displayString:
            # Get the ascii value and then subtract 32 as the font does not
            # have any characters before the 32nd implemented.
            fontIndex = ord(c) - 32
            self.__sendData(self.font1[fontIndex])
            self.__sendDataByte(0x00)

    def centerString(self, inString, row):
        inString = str(inString)
        if len(inString) > 21:
            return
        startPosition = (131 - (6 * len(inString))) / 2
        self.displayString(inString, row, startPosition)

    def displayInvertedString(self, inString, row, col):
        # Convert string to all caps as lower case characters are not
        # implemented in the font.
        # displayString = str(inString).upper()
        displayString = inString
        # Set the row/column position
        self.setCursorPosition(row, col)
        for c in displayString:
            # Get the ascii value and then subtract 32 as the font does not
            # have any characters before the 32nd implemented.
            fontIndex = ord(c) - 32
            bytestream = self.font[fontIndex]
            for b in bytestream:
                # invert the byte and send it
                self.__sendDataByte(b ^ 0xFF)
            self.__sendDataByte(0xFF)
        self.setCursorPosition(row + 1, col)
        for c in displayString:
            # Get the ascii value and then subtract 32 as the font does not
            # have any characters before the 32nd implemented.
            fontIndex = ord(c) - 32
            bytestream = self.font1[fontIndex]
            for b in bytestream:
                # invert the byte and send it
                self.__sendDataByte(b ^ 0xFF)
            self.__sendDataByte(0xFF)

    def __displayProcessedImage(self, processedImage, row, col):
        """Takes an image that has already been processed and displays it on the LCD.
        The upper left corner of the picture starts at the coordinates indicated by
        row and col.

            processedImage - Pre-processed image.  Must be of type LCDImage below.
            row - Row (page) at which to start the upper left corner of the image
            col - Column at which to start the upper left corner of the image

        """
        try:
            # Ensure the picture will fit with the given column and row starting points.
            if (processedImage.width + col > 132) or (
                processedImage.height / 8 + row > 8
            ):
                raise ValueError(
                    "Picture is too large to fit on the screen with the"
                    + " supplied row/column: Width "
                    + str(processedImage.width)
                    + ", Height "
                    + str(processedImage.height)
                )
            # Get the raw data from the processed image
            imageData = processedImage.data

            # Display the image
            for i in range(row, 8):
                self.setCursorPosition(row, col)
                # Set column
                page = self.SET_PAGE_ADDR + i
                self.__sendCommand(page)
                # The i2c bus can only take a maximum of 32 bytes of data at a
                # time. If the image is more than 32 pixels wide we need to
                # break it into chunks.
                stream = imageData[i]
                if len(stream) > MAX_BUFFER_LENGTH:
                    splitStream = self.__chunks(list(stream), MAX_BUFFER_LENGTH)
                    for chunk in splitStream:
                        self.__sendData(chunk)
                else:
                    self.__sendData(stream)

        except ValueError:
            print("Value Error: ")
            traceback.print_exc()

    def __chunks(self, inList, chunkSize):
        for i in range(0, len(inList), chunkSize):
            yield inList[i : i + chunkSize]

    # ==============================================================================================
    #        Internal Classes
    # ==============================================================================================

    class LCDImage:
        """Takes a monochrome bitmap image and represents it in a form
        that is more easily displayed on the LCD.
        """

        def __init__(self, filename):
            self.width = 0
            self.height = 0
            self.data = self.processPicture(filename)

        def processPicture(self, filename):
            """Imports a monocrhome bitmap file and converts it into a format
            that can be displayed on the LCD.  The black pixels of the
            bitmap will be read as "ON", and white as "OFF" effectively
            reversing the colors on the actual LCD.
            *The bitmap cannot be larger than 132 pixels wide or 64 pixels
             tall.
            *The bitmap's height must be divisible by 8.

               filename - The bitmap file to import.

               Returns - a (list of lists) that can be passed into
                   the displayImage(filename)
            """

            output = []
            try:
                picture = Image.open(filename)
                width, height = picture.size
                # Ensure image file will fit within the limits of the LCD
                if width > 132 or height > 64:
                    raise ValueError(
                        "Picture is larger than the allowable 132x64 pixels."
                    )

                # Ensure image file height is divisible by 8
                # TODO - Should probably just change logic below to properly
                # handle this case.  Don't need it for now.
                if height % 8 != 0:
                    raise ValueError("Picture height is not divisible by 8.")

                # Properly set the width/height class variables
                self.width = width
                self.height = height

                # Read in the picture as a bitstream.
                bits = list(picture.getdata())

                # Convert stream of pixels to width x height array
                matrix = []
                for i in range(height):
                    temp = []
                    for j in range(width):
                        temp.append(bits[i * width + j])
                    matrix.append(temp)

                # Convert width x height array
                for i in range(height / 8):
                    temp = []
                    for j in range(width):
                        bit0 = matrix[i * 8][j] / 255
                        bit1 = 2 * (matrix[i * 8 + 1][j] / 255)
                        bit2 = 4 * (matrix[i * 8 + 2][j] / 255)
                        bit3 = 8 * (matrix[i * 8 + 3][j] / 255)
                        bit4 = 16 * (matrix[i * 8 + 4][j] / 255)
                        bit5 = 32 * (matrix[i * 8 + 5][j] / 255)
                        bit6 = 64 * (matrix[i * 8 + 6][j] / 255)
                        bit7 = 128 * (matrix[i * 8 + 7][j] / 255)
                        temp.append(
                            bit0 + bit1 + bit2 + bit3 + bit4 + bit5 + bit6 + bit7
                        )
                    output.append(temp)
            except IOError:
                print("I/O error: Could not open file: " + filename)
                traceback.print_exc()
            except ValueError:
                print("Value Error: ")
                traceback.print_exc()

            return output
