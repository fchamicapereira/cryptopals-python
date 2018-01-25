import base64
import binascii 
import codecs
import copy

class Binary:
    def __init__(self, data='', base=2, pad=None):
        self.decToHex = ['0','1','2','3','4','5','6','7','8','9','a','b','c','d','e','f']
        self.decToBin = [
            '0000', '0001', '0010', '0011',
            '0100', '0101', '0110', '0111',
            '1000', '1001', '1010', '1011',
            '1100', '1101', '1110', '1111',
        ]

        if base == 2:
            self.binary = data
        elif base == 10:
            self.fromDec(data, pad)
        elif base == 16:
            self.fromHex(data)
        elif base == 64:
            self.fromBase64(data)
        elif base == 128:
            self.fromAscii(data)

    #-----------------------------------
    #            FROM
    #-----------------------------------
    
    def fromDec(self, d, pad=None):
        result = ''

        while d > 0:
            result = str(d % 2) + result
            d = int(d / 2)
        
        while pad and len(result) < pad:
            result = '0' + result

        self.binary = result

    def fromHex(self, h):
        data = ''

        for digit in h:
            data = data + self.decToBin[self.decToHex.index(digit.lower())]
        
        self.binary = data

    def fromBase64(self, data):
        self.fromHex(binascii.hexlify(base64.b64decode(data)).decode("utf-8"))

    def fromAscii(self, ascii):
        data = ''
        for c in ascii:
            hex = format(ord(c), "x")
            if len(hex) == 1:
                hex = '0' + hex
            data = data + hex
        self.fromHex(data)

    #-----------------------------------
    #               TO
    #-----------------------------------

    def toDec(self):
        result = 0
        for i in range(len(self.binary)):
            if self.binary[len(self.binary) - 1 - i] == '1':
                result += pow(2,i)
        return result

    def toHex(self):
        result = ''
        for i in range(0, len(self.binary), 4):
            result  = result + self.decToHex[self.decToBin.index(self.binary[i:i+4])] 
        return result

    def toBase64(self):
        return base64.b64encode(binascii.unhexlify(self.toHex())).decode("utf-8")

    def toAscii(self):
        result = ''
        hex = self.toHex()
        return codecs.decode(hex, "hex").decode('utf-8')

    #-----------------------------------
    #             OPERATORS
    #-----------------------------------

    def __xor__(self, other):
        result = ''
        binary = self.binary

        division = int(len(binary) / len(other.binary))
        remainder = len(binary) % len(other.binary)
        
        other = other.binary * division + other.binary[:remainder]

        for i in range(len(binary)):
            if binary[i] == other[i]:
                result += '0'
            else:
                result += '1'

        newBinary = Binary(result)

        return newBinary

    def __eq__(self, other):
        if len(self.binary) != len(other.binary):
            return False

        for i in range(len(self.binary)):
            if self.binary[i] != other.binary[i]:
                return False

        return True

    def __getitem__(self, i):
        return self.binary[i]

    def __len__(self):
        return len(self.binary)

    def __str__(self):
        return self.binary

    #-----------------------------------
    #             OTHER
    #-----------------------------------

    def pkcs_7(self, size):
        result = self.binary
        missing = int((size - len(result)) / 8)
        add = Binary(missing, 10, 8)

        for byte in range(missing):
            result += add.binary
            
        return Binary(result)

class Line:
    def __init__(self, data, lineData=None):
        
        if lineData != None:
            if len(lineData) != 4:
                raise ValueError('Line must have 4 bytes (has {})'.format(len(lineData)))

            for byte in lineData:
                if len(byte) != 8:
                    raise ValueError('Byte in line must have 8 bits (has {})'.format(len(byte)))
            
            self.data = lineData
            return

        self.data = []

        if len(data) != 8*4:
            raise ValueError('Block must be 32 bits long (is {})'.format(len(data)))

        for n in range(0, len(data), 8):
            self.data.append(Binary(data[n:n+8]))
    
    def toBin(self):
        result = ''

        for byte in self.data:
            result += byte

        return result

    def rotate(self):
        temp = copy.deepcopy(self.data)
        temp.pop(0)
        temp.append(self.data[0])

        return Line('', temp)

    def __getitem__(self, i):
        return self.data[i]

    def __setitem__(self, key, value):
        self.data[key] = value

    def __str__(self):
        output = ''

        for byte in self.data:
            output += '| {} |\n'.format(byte.toHex())

        return output

    def __len__(self):
        return len(self.data)
    
    def __xor__(self, other):
        data = ''

        if len(self) != len(other):
            raise ValueError('Lines with different lengths\n{}VS{}'.format(str(self), str(other)))

        for byte in range(len(self)):
            data += str(self.data[byte] ^ other.data[byte])
        
        return Line(data)

class State:
    def __init__(self, data='', keySize=0, stateData=None):

        if keySize not in [128, 192, 256]:
            raise ValueError('Key must have 128, 192 or 256 bits (has {})'.format(keySize))

        if stateData != None:
            bits = 0

            if not isinstance(stateData, list) or not isinstance(stateData[0], Line):
                raise TypeError('stateData must be array of Lines (is {})'.format(type(stateData)))

            for line in stateData:
                if len(line) != 4:
                    raise ValueError('Line must have 4 bytes (has {})'.format(len(line)))
                for byte in line:
                    if len(byte) != 8:
                        raise ValueError('Byte in line must have 8 bits (has {})'.format(len(byte)))
                    bits += len(byte)

            if bits > keySize:
                raise ValueError('State must not have more bits than keySize ({} vs {}}'.format(bits, keySize))

            self.data = stateData
            return

        self.data = []
        data = copy.deepcopy(data)

        if len(data) < keySize:
            size = keySize * (int(len(data) / keySize) + 1)
            data = str(Binary(data).pkcs_7(size))

        if len(data) > keySize:
            raise ValueError('Data and keySize must have the same size (data: {}, keysize len: {})'.format(len(data), keySize))

        for line in range(0, keySize, 32):
            self.data.append(Line(data[line:line+32]))
    
    def lenLines(self):
        return len(self.data)

    def append(self, line):
        if self.lenLines() == 4:
            return False

        if not isinstance(line, Line):
            raise TypeError('Append function receives Line instead of {}'.format(type(line)))
        
        if len(line) != 4:
            raise ValueError('Line in append function does not have 4 bytes')
        
        self.data.append(line)

        return True

    def __getitem__(self, i):
        return self.data[i]

    def __setitem__(self, key, value):
        self.data[key] = value

    def __xor__(self, other):
        if self.lenLines() != other.lenLines():
            raise ValueError('States with different lengths\n{}VS{}'.format(str(self), str(other)))

        newState = []
        for line in range(self.lenLines()):
            newState.append(self[line] ^ other[line])

        return State('', len(self) * 8, newState)
    
    def __len__(self):
        totalBytes = 0

        for line in self.data:
            totalBytes += len(line)
        
        return totalBytes

    def __str__(self):
        stateSize = len(self.data)
        lineSize = len(self.data[0])
        output = ''

        for byte in range(lineSize):
            output += '| '
            for line in range(stateSize):
                output += self.data[line][byte].toHex() + ' '
            output += '|\n'

        return output + '\n'

    def mul(self, matrix):
        mul2 = [
            0x00,0x02,0x04,0x06,0x08,0x0a,0x0c,0x0e,0x10,0x12,0x14,0x16,0x18,0x1a,0x1c,0x1e,
            0x20,0x22,0x24,0x26,0x28,0x2a,0x2c,0x2e,0x30,0x32,0x34,0x36,0x38,0x3a,0x3c,0x3e,
            0x40,0x42,0x44,0x46,0x48,0x4a,0x4c,0x4e,0x50,0x52,0x54,0x56,0x58,0x5a,0x5c,0x5e,
            0x60,0x62,0x64,0x66,0x68,0x6a,0x6c,0x6e,0x70,0x72,0x74,0x76,0x78,0x7a,0x7c,0x7e,
            0x80,0x82,0x84,0x86,0x88,0x8a,0x8c,0x8e,0x90,0x92,0x94,0x96,0x98,0x9a,0x9c,0x9e,
            0xa0,0xa2,0xa4,0xa6,0xa8,0xaa,0xac,0xae,0xb0,0xb2,0xb4,0xb6,0xb8,0xba,0xbc,0xbe,
            0xc0,0xc2,0xc4,0xc6,0xc8,0xca,0xcc,0xce,0xd0,0xd2,0xd4,0xd6,0xd8,0xda,0xdc,0xde,
            0xe0,0xe2,0xe4,0xe6,0xe8,0xea,0xec,0xee,0xf0,0xf2,0xf4,0xf6,0xf8,0xfa,0xfc,0xfe,
            0x1b,0x19,0x1f,0x1d,0x13,0x11,0x17,0x15,0x0b,0x09,0x0f,0x0d,0x03,0x01,0x07,0x05,
            0x3b,0x39,0x3f,0x3d,0x33,0x31,0x37,0x35,0x2b,0x29,0x2f,0x2d,0x23,0x21,0x27,0x25,
            0x5b,0x59,0x5f,0x5d,0x53,0x51,0x57,0x55,0x4b,0x49,0x4f,0x4d,0x43,0x41,0x47,0x45,
            0x7b,0x79,0x7f,0x7d,0x73,0x71,0x77,0x75,0x6b,0x69,0x6f,0x6d,0x63,0x61,0x67,0x65,
            0x9b,0x99,0x9f,0x9d,0x93,0x91,0x97,0x95,0x8b,0x89,0x8f,0x8d,0x83,0x81,0x87,0x85,
            0xbb,0xb9,0xbf,0xbd,0xb3,0xb1,0xb7,0xb5,0xab,0xa9,0xaf,0xad,0xa3,0xa1,0xa7,0xa5,
            0xdb,0xd9,0xdf,0xdd,0xd3,0xd1,0xd7,0xd5,0xcb,0xc9,0xcf,0xcd,0xc3,0xc1,0xc7,0xc5,
            0xfb,0xf9,0xff,0xfd,0xf3,0xf1,0xf7,0xf5,0xeb,0xe9,0xef,0xed,0xe3,0xe1,0xe7,0xe5
        ]

        mul3 = [
            0x00,0x03,0x06,0x05,0x0c,0x0f,0x0a,0x09,0x18,0x1b,0x1e,0x1d,0x14,0x17,0x12,0x11,
            0x30,0x33,0x36,0x35,0x3c,0x3f,0x3a,0x39,0x28,0x2b,0x2e,0x2d,0x24,0x27,0x22,0x21,
            0x60,0x63,0x66,0x65,0x6c,0x6f,0x6a,0x69,0x78,0x7b,0x7e,0x7d,0x74,0x77,0x72,0x71,
            0x50,0x53,0x56,0x55,0x5c,0x5f,0x5a,0x59,0x48,0x4b,0x4e,0x4d,0x44,0x47,0x42,0x41,
            0xc0,0xc3,0xc6,0xc5,0xcc,0xcf,0xca,0xc9,0xd8,0xdb,0xde,0xdd,0xd4,0xd7,0xd2,0xd1,
            0xf0,0xf3,0xf6,0xf5,0xfc,0xff,0xfa,0xf9,0xe8,0xeb,0xee,0xed,0xe4,0xe7,0xe2,0xe1,
            0xa0,0xa3,0xa6,0xa5,0xac,0xaf,0xaa,0xa9,0xb8,0xbb,0xbe,0xbd,0xb4,0xb7,0xb2,0xb1,
            0x90,0x93,0x96,0x95,0x9c,0x9f,0x9a,0x99,0x88,0x8b,0x8e,0x8d,0x84,0x87,0x82,0x81,
            0x9b,0x98,0x9d,0x9e,0x97,0x94,0x91,0x92,0x83,0x80,0x85,0x86,0x8f,0x8c,0x89,0x8a,
            0xab,0xa8,0xad,0xae,0xa7,0xa4,0xa1,0xa2,0xb3,0xb0,0xb5,0xb6,0xbf,0xbc,0xb9,0xba,
            0xfb,0xf8,0xfd,0xfe,0xf7,0xf4,0xf1,0xf2,0xe3,0xe0,0xe5,0xe6,0xef,0xec,0xe9,0xea,
            0xcb,0xc8,0xcd,0xce,0xc7,0xc4,0xc1,0xc2,0xd3,0xd0,0xd5,0xd6,0xdf,0xdc,0xd9,0xda,
            0x5b,0x58,0x5d,0x5e,0x57,0x54,0x51,0x52,0x43,0x40,0x45,0x46,0x4f,0x4c,0x49,0x4a,
            0x6b,0x68,0x6d,0x6e,0x67,0x64,0x61,0x62,0x73,0x70,0x75,0x76,0x7f,0x7c,0x79,0x7a,
            0x3b,0x38,0x3d,0x3e,0x37,0x34,0x31,0x32,0x23,0x20,0x25,0x26,0x2f,0x2c,0x29,0x2a,
            0x0b,0x08,0x0d,0x0e,0x07,0x04,0x01,0x02,0x13,0x10,0x15,0x16,0x1f,0x1c,0x19,0x1a
        ]

        mul9 = [
            0x00,0x09,0x12,0x1b,0x24,0x2d,0x36,0x3f,0x48,0x41,0x5a,0x53,0x6c,0x65,0x7e,0x77,
            0x90,0x99,0x82,0x8b,0xb4,0xbd,0xa6,0xaf,0xd8,0xd1,0xca,0xc3,0xfc,0xf5,0xee,0xe7,
            0x3b,0x32,0x29,0x20,0x1f,0x16,0x0d,0x04,0x73,0x7a,0x61,0x68,0x57,0x5e,0x45,0x4c,
            0xab,0xa2,0xb9,0xb0,0x8f,0x86,0x9d,0x94,0xe3,0xea,0xf1,0xf8,0xc7,0xce,0xd5,0xdc,
            0x76,0x7f,0x64,0x6d,0x52,0x5b,0x40,0x49,0x3e,0x37,0x2c,0x25,0x1a,0x13,0x08,0x01,
            0xe6,0xef,0xf4,0xfd,0xc2,0xcb,0xd0,0xd9,0xae,0xa7,0xbc,0xb5,0x8a,0x83,0x98,0x91,
            0x4d,0x44,0x5f,0x56,0x69,0x60,0x7b,0x72,0x05,0x0c,0x17,0x1e,0x21,0x28,0x33,0x3a,
            0xdd,0xd4,0xcf,0xc6,0xf9,0xf0,0xeb,0xe2,0x95,0x9c,0x87,0x8e,0xb1,0xb8,0xa3,0xaa,
            0xec,0xe5,0xfe,0xf7,0xc8,0xc1,0xda,0xd3,0xa4,0xad,0xb6,0xbf,0x80,0x89,0x92,0x9b,
            0x7c,0x75,0x6e,0x67,0x58,0x51,0x4a,0x43,0x34,0x3d,0x26,0x2f,0x10,0x19,0x02,0x0b,
            0xd7,0xde,0xc5,0xcc,0xf3,0xfa,0xe1,0xe8,0x9f,0x96,0x8d,0x84,0xbb,0xb2,0xa9,0xa0,
            0x47,0x4e,0x55,0x5c,0x63,0x6a,0x71,0x78,0x0f,0x06,0x1d,0x14,0x2b,0x22,0x39,0x30,
            0x9a,0x93,0x88,0x81,0xbe,0xb7,0xac,0xa5,0xd2,0xdb,0xc0,0xc9,0xf6,0xff,0xe4,0xed,
            0x0a,0x03,0x18,0x11,0x2e,0x27,0x3c,0x35,0x42,0x4b,0x50,0x59,0x66,0x6f,0x74,0x7d,
            0xa1,0xa8,0xb3,0xba,0x85,0x8c,0x97,0x9e,0xe9,0xe0,0xfb,0xf2,0xcd,0xc4,0xdf,0xd6,
            0x31,0x38,0x23,0x2a,0x15,0x1c,0x07,0x0e,0x79,0x70,0x6b,0x62,0x5d,0x54,0x4f,0x46
        ]

        mul11 = [
            0x00,0x0b,0x16,0x1d,0x2c,0x27,0x3a,0x31,0x58,0x53,0x4e,0x45,0x74,0x7f,0x62,0x69,
            0xb0,0xbb,0xa6,0xad,0x9c,0x97,0x8a,0x81,0xe8,0xe3,0xfe,0xf5,0xc4,0xcf,0xd2,0xd9,
            0x7b,0x70,0x6d,0x66,0x57,0x5c,0x41,0x4a,0x23,0x28,0x35,0x3e,0x0f,0x04,0x19,0x12,
            0xcb,0xc0,0xdd,0xd6,0xe7,0xec,0xf1,0xfa,0x93,0x98,0x85,0x8e,0xbf,0xb4,0xa9,0xa2,
            0xf6,0xfd,0xe0,0xeb,0xda,0xd1,0xcc,0xc7,0xae,0xa5,0xb8,0xb3,0x82,0x89,0x94,0x9f,
            0x46,0x4d,0x50,0x5b,0x6a,0x61,0x7c,0x77,0x1e,0x15,0x08,0x03,0x32,0x39,0x24,0x2f,
            0x8d,0x86,0x9b,0x90,0xa1,0xaa,0xb7,0xbc,0xd5,0xde,0xc3,0xc8,0xf9,0xf2,0xef,0xe4,
            0x3d,0x36,0x2b,0x20,0x11,0x1a,0x07,0x0c,0x65,0x6e,0x73,0x78,0x49,0x42,0x5f,0x54,
            0xf7,0xfc,0xe1,0xea,0xdb,0xd0,0xcd,0xc6,0xaf,0xa4,0xb9,0xb2,0x83,0x88,0x95,0x9e,
            0x47,0x4c,0x51,0x5a,0x6b,0x60,0x7d,0x76,0x1f,0x14,0x09,0x02,0x33,0x38,0x25,0x2e,
            0x8c,0x87,0x9a,0x91,0xa0,0xab,0xb6,0xbd,0xd4,0xdf,0xc2,0xc9,0xf8,0xf3,0xee,0xe5,
            0x3c,0x37,0x2a,0x21,0x10,0x1b,0x06,0x0d,0x64,0x6f,0x72,0x79,0x48,0x43,0x5e,0x55,
            0x01,0x0a,0x17,0x1c,0x2d,0x26,0x3b,0x30,0x59,0x52,0x4f,0x44,0x75,0x7e,0x63,0x68,
            0xb1,0xba,0xa7,0xac,0x9d,0x96,0x8b,0x80,0xe9,0xe2,0xff,0xf4,0xc5,0xce,0xd3,0xd8,
            0x7a,0x71,0x6c,0x67,0x56,0x5d,0x40,0x4b,0x22,0x29,0x34,0x3f,0x0e,0x05,0x18,0x13,
            0xca,0xc1,0xdc,0xd7,0xe6,0xed,0xf0,0xfb,0x92,0x99,0x84,0x8f,0xbe,0xb5,0xa8,0xa3
        ]

        mul13 = [
            0x00,0x0d,0x1a,0x17,0x34,0x39,0x2e,0x23,0x68,0x65,0x72,0x7f,0x5c,0x51,0x46,0x4b,
            0xd0,0xdd,0xca,0xc7,0xe4,0xe9,0xfe,0xf3,0xb8,0xb5,0xa2,0xaf,0x8c,0x81,0x96,0x9b,
            0xbb,0xb6,0xa1,0xac,0x8f,0x82,0x95,0x98,0xd3,0xde,0xc9,0xc4,0xe7,0xea,0xfd,0xf0,
            0x6b,0x66,0x71,0x7c,0x5f,0x52,0x45,0x48,0x03,0x0e,0x19,0x14,0x37,0x3a,0x2d,0x20,
            0x6d,0x60,0x77,0x7a,0x59,0x54,0x43,0x4e,0x05,0x08,0x1f,0x12,0x31,0x3c,0x2b,0x26,
            0xbd,0xb0,0xa7,0xaa,0x89,0x84,0x93,0x9e,0xd5,0xd8,0xcf,0xc2,0xe1,0xec,0xfb,0xf6,
            0xd6,0xdb,0xcc,0xc1,0xe2,0xef,0xf8,0xf5,0xbe,0xb3,0xa4,0xa9,0x8a,0x87,0x90,0x9d,
            0x06,0x0b,0x1c,0x11,0x32,0x3f,0x28,0x25,0x6e,0x63,0x74,0x79,0x5a,0x57,0x40,0x4d,
            0xda,0xd7,0xc0,0xcd,0xee,0xe3,0xf4,0xf9,0xb2,0xbf,0xa8,0xa5,0x86,0x8b,0x9c,0x91,
            0x0a,0x07,0x10,0x1d,0x3e,0x33,0x24,0x29,0x62,0x6f,0x78,0x75,0x56,0x5b,0x4c,0x41,
            0x61,0x6c,0x7b,0x76,0x55,0x58,0x4f,0x42,0x09,0x04,0x13,0x1e,0x3d,0x30,0x27,0x2a,
            0xb1,0xbc,0xab,0xa6,0x85,0x88,0x9f,0x92,0xd9,0xd4,0xc3,0xce,0xed,0xe0,0xf7,0xfa,
            0xb7,0xba,0xad,0xa0,0x83,0x8e,0x99,0x94,0xdf,0xd2,0xc5,0xc8,0xeb,0xe6,0xf1,0xfc,
            0x67,0x6a,0x7d,0x70,0x53,0x5e,0x49,0x44,0x0f,0x02,0x15,0x18,0x3b,0x36,0x21,0x2c,
            0x0c,0x01,0x16,0x1b,0x38,0x35,0x22,0x2f,0x64,0x69,0x7e,0x73,0x50,0x5d,0x4a,0x47,
            0xdc,0xd1,0xc6,0xcb,0xe8,0xe5,0xf2,0xff,0xb4,0xb9,0xae,0xa3,0x80,0x8d,0x9a,0x97
        ]

        mul14 = [
            0x00,0x0e,0x1c,0x12,0x38,0x36,0x24,0x2a,0x70,0x7e,0x6c,0x62,0x48,0x46,0x54,0x5a,
            0xe0,0xee,0xfc,0xf2,0xd8,0xd6,0xc4,0xca,0x90,0x9e,0x8c,0x82,0xa8,0xa6,0xb4,0xba,
            0xdb,0xd5,0xc7,0xc9,0xe3,0xed,0xff,0xf1,0xab,0xa5,0xb7,0xb9,0x93,0x9d,0x8f,0x81,
            0x3b,0x35,0x27,0x29,0x03,0x0d,0x1f,0x11,0x4b,0x45,0x57,0x59,0x73,0x7d,0x6f,0x61,
            0xad,0xa3,0xb1,0xbf,0x95,0x9b,0x89,0x87,0xdd,0xd3,0xc1,0xcf,0xe5,0xeb,0xf9,0xf7,
            0x4d,0x43,0x51,0x5f,0x75,0x7b,0x69,0x67,0x3d,0x33,0x21,0x2f,0x05,0x0b,0x19,0x17,
            0x76,0x78,0x6a,0x64,0x4e,0x40,0x52,0x5c,0x06,0x08,0x1a,0x14,0x3e,0x30,0x22,0x2c,
            0x96,0x98,0x8a,0x84,0xae,0xa0,0xb2,0xbc,0xe6,0xe8,0xfa,0xf4,0xde,0xd0,0xc2,0xcc,
            0x41,0x4f,0x5d,0x53,0x79,0x77,0x65,0x6b,0x31,0x3f,0x2d,0x23,0x09,0x07,0x15,0x1b,
            0xa1,0xaf,0xbd,0xb3,0x99,0x97,0x85,0x8b,0xd1,0xdf,0xcd,0xc3,0xe9,0xe7,0xf5,0xfb,
            0x9a,0x94,0x86,0x88,0xa2,0xac,0xbe,0xb0,0xea,0xe4,0xf6,0xf8,0xd2,0xdc,0xce,0xc0,
            0x7a,0x74,0x66,0x68,0x42,0x4c,0x5e,0x50,0x0a,0x04,0x16,0x18,0x32,0x3c,0x2e,0x20,
            0xec,0xe2,0xf0,0xfe,0xd4,0xda,0xc8,0xc6,0x9c,0x92,0x80,0x8e,0xa4,0xaa,0xb8,0xb6,
            0x0c,0x02,0x10,0x1e,0x34,0x3a,0x28,0x26,0x7c,0x72,0x60,0x6e,0x44,0x4a,0x58,0x56,
            0x37,0x39,0x2b,0x25,0x0f,0x01,0x13,0x1d,0x47,0x49,0x5b,0x55,0x7f,0x71,0x63,0x6d,
            0xd7,0xd9,0xcb,0xc5,0xef,0xe1,0xf3,0xfd,0xa7,0xa9,0xbb,0xb5,0x9f,0x91,0x83,0x8d
        ]

        newState = []

        for line in range(self.lenLines()):
            newLine = []
            for matrixByte in range(len(matrix[0])):
                newValue = Binary('00', 16)
                for matrixLine in range(len(matrix)):
                    if matrix[matrixLine][matrixByte] == 1:
                        newValue = newValue ^ self[line][matrixLine]
                    elif matrix[matrixLine][matrixByte] == 2:
                        newValue = newValue ^ Binary(format(mul2[self[line][matrixLine].toDec()], '02x'), 16)
                    elif matrix[matrixLine][matrixByte] == 3:
                        newValue = newValue ^ Binary(format(mul3[self[line][matrixLine].toDec()], '02x'), 16)
                    elif matrix[matrixLine][matrixByte] == 9:
                        newValue = newValue ^ Binary(format(mul9[self[line][matrixLine].toDec()], '02x'), 16)
                    elif matrix[matrixLine][matrixByte] == 11:
                        newValue = newValue ^ Binary(format(mul11[self[line][matrixLine].toDec()], '02x'), 16)
                    elif matrix[matrixLine][matrixByte] == 13:
                        newValue = newValue ^ Binary(format(mul13[self[line][matrixLine].toDec()], '02x'), 16)
                    else:
                        newValue = newValue ^ Binary(format(mul14[self[line][matrixLine].toDec()], '02x'), 16)
                newLine.append(newValue)
            self[line] = Line('', newLine)

    def getData(self):
        data = ''
        for line in self.data:
            for byte in line:
                data += byte.binary
        return data

class Crypto:
    def __init__(self, encodedData, base=2):
        self.data = Binary(encodedData, base)
        self.roundKeys = []
        self.cipherText = None

    @classmethod
    def englishLetterFreqScore(cls, data):
        letterFreq = {
            'a':	0.08167, 'b':	0.01492,
            'c':	0.02782, 'd':	0.04253,
            'e':	0.12702, 'f':	0.02228,
            'g':	0.02015, 'h':	0.06094,
            'i':	0.06966, 'j':	0.00153,
            'k':	0.00772, 'l':	0.04025,
            'm':	0.02406, 'n':	0.06749,
            'o':	0.07507, 'p':	0.01929,
            'q':	0.00095, 'r':	0.05987,
            's':	0.06327, 't':	0.09056,
            'u':	0.02758, 'v':	0.00978,
            'w':	0.02360, 'x':	0.00150,
            'y':	0.01974, 'z':	0.00074
        }
        score = 1

        try:
            ascii = data.toAscii().lower()
        except UnicodeDecodeError:
            return 0

        for c in ascii:
            if c in letterFreq:
                score += letterFreq[c] * len(ascii)
            elif c == ' ':
                score += len(ascii)
            elif ord(c) < 32:
                score -= len(ascii) * 2

        return score

    @classmethod
    def hammingDist(cls, b1, b2):
        hd = 0

        while len(b1) > len(b2) or len(b1) < len(b2):
            if len(b1) > len(b2):
                b2 = '0' + b2
            elif len(b1) < len(b2):
                b1 = '0' + b1

        for i in range(len(b1)):
            if b1[i] != b2[i]:
                hd += 1
        
        return hd

    #-----------------------------------
    #                XOR
    #-----------------------------------

    def xor(self, key):
        self.data = self.data ^ key

    def decSingleCharXOR(self):
        key = Binary()
        bestResult = (0, '', '') # (score, key, decodedText)

        for c in range(128):
            key.fromAscii(chr(c))
            score = self.englishLetterFreqScore(self.data ^ key)

            if score > bestResult[0]:
                bestResult = (score, chr(c), (self.data ^ key).toAscii())
        return bestResult

    def decXOR(self):
        keysizes = []

        for keysize in range(2, 40):
            firstPacket = self.data[:keysize * 8]
            secondPacket = self.data[2*(keysize * 8):3*(keysize * 8)]
            thirdPacket = self.data[3*(keysize * 8):4*(keysize * 8)]
            fourthPacket = self.data[4*(keysize * 8):5*(keysize * 8)]

            result = self.hammingDist(firstPacket, secondPacket)
            result += self.hammingDist(firstPacket, thirdPacket)
            result += self.hammingDist(firstPacket, fourthPacket)
            result += self.hammingDist(secondPacket, thirdPacket)
            result += self.hammingDist(secondPacket, fourthPacket)
            result += self.hammingDist(thirdPacket, fourthPacket)
            result /= keysize * 6

            keysizes.append((result, keysize))

        keysizes = sorted(keysizes, key=lambda tup: tup[0])
        keys = []

        for i in range(2):
            keysize = keysizes[i][1]
            data = [self.data[i:i + keysize * 8] for i in range(0, len(self.data), keysize * 8)]

            key = ''
            for byte in range(keysize):
                grabbedBytes = ''

                for block in data:
                    grabbedBytes += block[byte*8:byte*8+8]
                
                key += Crypto(grabbedBytes).decSingleCharXOR()[1]
            keys.append(key)
        
        return keys

    #-----------------------------------
    #               AES
    #-----------------------------------

    @classmethod
    def getStates(cls, data, keySize):
        states = []

        if keySize not in [128, 192, 256]:
            raise ValueError('Key must have 128, 192 or 256 bits (has {})'.format(keySize))

        for n in range(0, len(data), keySize):
            states.append(State(data[n:n+keySize], keySize))

        return states

    @classmethod
    def bytesInStates(cls, states):
        result = 0

        for state in states:
            result += len(state)

        return result

    @classmethod
    def rcon(cls, i, byte):
        rcon = [
            0x8d, 0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x40, 0x80, 0x1b, 0x36, 0x6c, 0xd8, 0xab, 0x4d, 0x9a, 
            0x2f, 0x5e, 0xbc, 0x63, 0xc6, 0x97, 0x35, 0x6a, 0xd4, 0xb3, 0x7d, 0xfa, 0xef, 0xc5, 0x91, 0x39, 
            0x72, 0xe4, 0xd3, 0xbd, 0x61, 0xc2, 0x9f, 0x25, 0x4a, 0x94, 0x33, 0x66, 0xcc, 0x83, 0x1d, 0x3a, 
            0x74, 0xe8, 0xcb, 0x8d, 0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x40, 0x80, 0x1b, 0x36, 0x6c, 0xd8, 
            0xab, 0x4d, 0x9a, 0x2f, 0x5e, 0xbc, 0x63, 0xc6, 0x97, 0x35, 0x6a, 0xd4, 0xb3, 0x7d, 0xfa, 0xef, 
            0xc5, 0x91, 0x39, 0x72, 0xe4, 0xd3, 0xbd, 0x61, 0xc2, 0x9f, 0x25, 0x4a, 0x94, 0x33, 0x66, 0xcc, 
            0x83, 0x1d, 0x3a, 0x74, 0xe8, 0xcb, 0x8d, 0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x40, 0x80, 0x1b, 
            0x36, 0x6c, 0xd8, 0xab, 0x4d, 0x9a, 0x2f, 0x5e, 0xbc, 0x63, 0xc6, 0x97, 0x35, 0x6a, 0xd4, 0xb3, 
            0x7d, 0xfa, 0xef, 0xc5, 0x91, 0x39, 0x72, 0xe4, 0xd3, 0xbd, 0x61, 0xc2, 0x9f, 0x25, 0x4a, 0x94, 
            0x33, 0x66, 0xcc, 0x83, 0x1d, 0x3a, 0x74, 0xe8, 0xcb, 0x8d, 0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 
            0x40, 0x80, 0x1b, 0x36, 0x6c, 0xd8, 0xab, 0x4d, 0x9a, 0x2f, 0x5e, 0xbc, 0x63, 0xc6, 0x97, 0x35, 
            0x6a, 0xd4, 0xb3, 0x7d, 0xfa, 0xef, 0xc5, 0x91, 0x39, 0x72, 0xe4, 0xd3, 0xbd, 0x61, 0xc2, 0x9f, 
            0x25, 0x4a, 0x94, 0x33, 0x66, 0xcc, 0x83, 0x1d, 0x3a, 0x74, 0xe8, 0xcb, 0x8d, 0x01, 0x02, 0x04, 
            0x08, 0x10, 0x20, 0x40, 0x80, 0x1b, 0x36, 0x6c, 0xd8, 0xab, 0x4d, 0x9a, 0x2f, 0x5e, 0xbc, 0x63, 
            0xc6, 0x97, 0x35, 0x6a, 0xd4, 0xb3, 0x7d, 0xfa, 0xef, 0xc5, 0x91, 0x39, 0x72, 0xe4, 0xd3, 0xbd, 
            0x61, 0xc2, 0x9f, 0x25, 0x4a, 0x94, 0x33, 0x66, 0xcc, 0x83, 0x1d, 0x3a, 0x74, 0xe8, 0xcb, 0x8d
        ]

        r = Binary(format(rcon[i], '02x'), 16)

        return byte ^ r

    @classmethod
    def sbox(cls, line):
        sbox = [
            0x63, 0x7C, 0x77, 0x7B, 0xF2, 0x6B, 0x6F, 0xC5, 0x30, 0x01, 0x67, 0x2B, 0xFE, 0xD7, 0xAB, 0x76,
            0xCA, 0x82, 0xC9, 0x7D, 0xFA, 0x59, 0x47, 0xF0, 0xAD, 0xD4, 0xA2, 0xAF, 0x9C, 0xA4, 0x72, 0xC0,
            0xB7, 0xFD, 0x93, 0x26, 0x36, 0x3F, 0xF7, 0xCC, 0x34, 0xA5, 0xE5, 0xF1, 0x71, 0xD8, 0x31, 0x15,
            0x04, 0xC7, 0x23, 0xC3, 0x18, 0x96, 0x05, 0x9A, 0x07, 0x12, 0x80, 0xE2, 0xEB, 0x27, 0xB2, 0x75,
            0x09, 0x83, 0x2C, 0x1A, 0x1B, 0x6E, 0x5A, 0xA0, 0x52, 0x3B, 0xD6, 0xB3, 0x29, 0xE3, 0x2F, 0x84,
            0x53, 0xD1, 0x00, 0xED, 0x20, 0xFC, 0xB1, 0x5B, 0x6A, 0xCB, 0xBE, 0x39, 0x4A, 0x4C, 0x58, 0xCF,
            0xD0, 0xEF, 0xAA, 0xFB, 0x43, 0x4D, 0x33, 0x85, 0x45, 0xF9, 0x02, 0x7F, 0x50, 0x3C, 0x9F, 0xA8,
            0x51, 0xA3, 0x40, 0x8F, 0x92, 0x9D, 0x38, 0xF5, 0xBC, 0xB6, 0xDA, 0x21, 0x10, 0xFF, 0xF3, 0xD2,
            0xCD, 0x0C, 0x13, 0xEC, 0x5F, 0x97, 0x44, 0x17, 0xC4, 0xA7, 0x7E, 0x3D, 0x64, 0x5D, 0x19, 0x73,
            0x60, 0x81, 0x4F, 0xDC, 0x22, 0x2A, 0x90, 0x88, 0x46, 0xEE, 0xB8, 0x14, 0xDE, 0x5E, 0x0B, 0xDB,
            0xE0, 0x32, 0x3A, 0x0A, 0x49, 0x06, 0x24, 0x5C, 0xC2, 0xD3, 0xAC, 0x62, 0x91, 0x95, 0xE4, 0x79,
            0xE7, 0xC8, 0x37, 0x6D, 0x8D, 0xD5, 0x4E, 0xA9, 0x6C, 0x56, 0xF4, 0xEA, 0x65, 0x7A, 0xAE, 0x08,
            0xBA, 0x78, 0x25, 0x2E, 0x1C, 0xA6, 0xB4, 0xC6, 0xE8, 0xDD, 0x74, 0x1F, 0x4B, 0xBD, 0x8B, 0x8A,
            0x70, 0x3E, 0xB5, 0x66, 0x48, 0x03, 0xF6, 0x0E, 0x61, 0x35, 0x57, 0xB9, 0x86, 0xC1, 0x1D, 0x9E,
            0xE1, 0xF8, 0x98, 0x11, 0x69, 0xD9, 0x8E, 0x94, 0x9B, 0x1E, 0x87, 0xE9, 0xCE, 0x55, 0x28, 0xDF,
            0x8C, 0xA1, 0x89, 0x0D, 0xBF, 0xE6, 0x42, 0x68, 0x41, 0x99, 0x2D, 0x0F, 0xB0, 0x54, 0xBB, 0x16
        ]

        result = []

        for byte in line:
            result.append(Binary(format(sbox[byte.toDec()], '02x'), 16))

        return Line('', result)

    @classmethod
    def sbox_inv(cls, line):
        sbox = [
            0x52, 0x09, 0x6A, 0xD5, 0x30, 0x36, 0xA5, 0x38, 0xBF, 0x40, 0xA3, 0x9E, 0x81, 0xF3, 0xD7, 0xFB,
            0x7C, 0xE3, 0x39, 0x82, 0x9B, 0x2F, 0xFF, 0x87, 0x34, 0x8E, 0x43, 0x44, 0xC4, 0xDE, 0xE9, 0xCB,
            0x54, 0x7B, 0x94, 0x32, 0xA6, 0xC2, 0x23, 0x3D, 0xEE, 0x4C, 0x95, 0x0B, 0x42, 0xFA, 0xC3, 0x4E,
            0x08, 0x2E, 0xA1, 0x66, 0x28, 0xD9, 0x24, 0xB2, 0x76, 0x5B, 0xA2, 0x49, 0x6D, 0x8B, 0xD1, 0x25,
            0x72, 0xF8, 0xF6, 0x64, 0x86, 0x68, 0x98, 0x16, 0xD4, 0xA4, 0x5C, 0xCC, 0x5D, 0x65, 0xB6, 0x92,
            0x6C, 0x70, 0x48, 0x50, 0xFD, 0xED, 0xB9, 0xDA, 0x5E, 0x15, 0x46, 0x57, 0xA7, 0x8D, 0x9D, 0x84,
            0x90, 0xD8, 0xAB, 0x00, 0x8C, 0xBC, 0xD3, 0x0A, 0xF7, 0xE4, 0x58, 0x05, 0xB8, 0xB3, 0x45, 0x06,
            0xD0, 0x2C, 0x1E, 0x8F, 0xCA, 0x3F, 0x0F, 0x02, 0xC1, 0xAF, 0xBD, 0x03, 0x01, 0x13, 0x8A, 0x6B,
            0x3A, 0x91, 0x11, 0x41, 0x4F, 0x67, 0xDC, 0xEA, 0x97, 0xF2, 0xCF, 0xCE, 0xF0, 0xB4, 0xE6, 0x73,
            0x96, 0xAC, 0x74, 0x22, 0xE7, 0xAD, 0x35, 0x85, 0xE2, 0xF9, 0x37, 0xE8, 0x1C, 0x75, 0xDF, 0x6E,
            0x47, 0xF1, 0x1A, 0x71, 0x1D, 0x29, 0xC5, 0x89, 0x6F, 0xB7, 0x62, 0x0E, 0xAA, 0x18, 0xBE, 0x1B,
            0xFC, 0x56, 0x3E, 0x4B, 0xC6, 0xD2, 0x79, 0x20, 0x9A, 0xDB, 0xC0, 0xFE, 0x78, 0xCD, 0x5A, 0xF4,
            0x1F, 0xDD, 0xA8, 0x33, 0x88, 0x07, 0xC7, 0x31, 0xB1, 0x12, 0x10, 0x59, 0x27, 0x80, 0xEC, 0x5F,
            0x60, 0x51, 0x7F, 0xA9, 0x19, 0xB5, 0x4A, 0x0D, 0x2D, 0xE5, 0x7A, 0x9F, 0x93, 0xC9, 0x9C, 0xEF,
            0xA0, 0xE0, 0x3B, 0x4D, 0xAE, 0x2A, 0xF5, 0xB0, 0xC8, 0xEB, 0xBB, 0x3C, 0x83, 0x53, 0x99, 0x61,
            0x17, 0x2B, 0x04, 0x7E, 0xBA, 0x77, 0xD6, 0x26, 0xE1, 0x69, 0x14, 0x63, 0x55, 0x21, 0x0C, 0x7D
        ]

        result = []

        for byte in line:
            result.append(Binary(format(sbox[byte.toDec()], '02x'), 16))

        return Line('', result)

    @classmethod
    def keySchedule(cls, key):
        def keyScheduleCore(i, line):
            result = cls.sbox(line.rotate())
            result[0] = cls.rcon(i, result[0])
            return result

        def getPreviousLine(states):
            nStates = len(states)
            nLines = states[nStates - 1].lenLines()
            return states[nStates - 1][nLines - 1]

        def getnTimesBeforeLine(states, n):
            lineIteration = int(n / 4)
            nStates = len(states)
            nLines = states[nStates - 1].lenLines()

            for s in range(nStates - 1, -1, -1):
                for l in range(states[s].lenLines() - 1, -1, -1):
                    lineIteration -= 1
                    if lineIteration == 0:
                        return states[s][l]

        keySize = len(key[0]) * 8
        n = 16 #bytes for 128-bit key value
        b = 176 #bytes for 128-bit key value
        rcon = 1
        expandedKey = copy.deepcopy(key)

        while cls.bytesInStates(expandedKey) < b:
            t = copy.deepcopy(getPreviousLine(expandedKey))
            t = keyScheduleCore(rcon, t)
            rcon += 1
            t = t ^ getnTimesBeforeLine(expandedKey, n)

            expandedKey.append(State('', keySize, [copy.deepcopy(t)]))

            for i in range(3):
                t = copy.deepcopy(getPreviousLine(expandedKey))
                t = t ^ getnTimesBeforeLine(expandedKey, n)
                expandedKey[len(expandedKey) - 1].append(copy.deepcopy(t))

        return expandedKey

    @classmethod
    def subBytes(cls, state):
        for line in range(state.lenLines()):
            state[line] = cls.sbox(state[line])

    @classmethod
    def subBytes_inv(cls, state):
        for line in range(state.lenLines()):
            state[line] = cls.sbox_inv(state[line])

    @classmethod
    def shiftRow(cls, state, row):
        temp = copy.deepcopy(state[0][row])
        state[0][row] = state[1][row]
        state[1][row] = state[2][row]
        state[2][row] = state[3][row]
        state[3][row] = temp
    
    @classmethod
    def shiftRow_inv(cls, state, row):
        temp = copy.deepcopy(state[3][row])
        state[3][row] = state[2][row]
        state[2][row] = state[1][row]
        state[1][row] = state[0][row]
        state[0][row] = temp

    @classmethod
    def shiftRows(cls, state):
        for row in range(state.lenLines()):
            for shift in range(0, row):
                cls.shiftRow(state, row)
    
    @classmethod
    def shiftRows_inv(cls, state):
        for row in range(state.lenLines()):
            for shift in range(0, row):
                cls.shiftRow_inv(state, row)

    @classmethod
    def mixColumns(cls, state):
        matrix = [
            [ 2, 1, 1, 3 ],
            [ 3, 2, 1, 1 ],
            [ 1, 3, 2, 1 ],
            [ 1, 1, 3, 2 ]
        ]

        state = state.mul(matrix)

    @classmethod
    def mixColumns_inv(cls, state):
        matrix = [
            [ 14, 9, 13, 11 ],
            [ 11, 14, 9, 13 ],
            [ 13, 11, 14, 9 ],
            [ 9, 13, 11, 14 ]
        ]

        state = state.mul(matrix)
    
    @classmethod
    def removePadding(cls, text):
        size = len(text)
        padNumber = Binary(text[-8:]).toDec()
        counter = 0

        if padNumber >= 32 or padNumber == 0:
            return text

        for digitPlace in range(len(text) - 8,len(text) - 8 - padNumber * 8, -8):
            digit = Binary(text[digitPlace:digitPlace + 8]).toDec()
            
            if digit != padNumber:
                return text
        
        for i in range(padNumber):
            text = text[:len(text) - 8]

        return text

    def encAES(self, state, key):
        cipherText = ''
        keySize = len(key)

        if not len(self.roundKeys):
            self.roundKeys = self.keySchedule(self.getStates(key, keySize))

        if keySize == 128:
            rounds = 10
        elif keySize == 192:
            rounds = 12
        elif keySize == 256:
            rounds = 14

        state = state ^ self.roundKeys[0]

        for round in range(1, rounds + 1):

            self.subBytes(state)

            self.shiftRows(state)

            if round < rounds:
                self.mixColumns(state)
            
            state = state ^ self.roundKeys[round]

        return state

    def decAES(self, state, key):
        cipherText = ''
        keySize = len(key)

        if not len(self.roundKeys):
            self.roundKeys = self.keySchedule(self.getStates(key, keySize))

        if keySize == 128:
            rounds = 10
        elif keySize == 192:
            rounds = 12
        elif keySize == 256:
            rounds = 14

        state = state ^ self.roundKeys[rounds]
        self.shiftRows_inv(state)
        self.subBytes_inv(state)

        for round in range(rounds - 1, 0, -1):
            state = state ^ self.roundKeys[round]
            self.mixColumns_inv(state)
            self.shiftRows_inv(state)
            self.subBytes_inv(state)

            
        state = state ^ self.roundKeys[0]
        
        return state


    def encAES_ECB(self, key):
        keySize = len(key)
        plainTextstates = self.getStates(self.data, keySize)
        data = ''

        for state in plainTextstates:
            data += self.encAES(state, key).getData()

        self.data = Binary(data)
    
    def decAES_ECB(self, key):
        keySize = len(key)
        cipherTextStates = self.getStates(self.data, keySize)
        data = ''

        for state in cipherTextStates:
            data += self.decAES(state, key).getData()
        
        self.data = Binary(self.removePadding(data))

    def encAES_CBC(self, key, IV):
        keySize = len(key)
        plainTextstates = self.getStates(self.data, keySize)
        IVstate = State(str(IV), keySize)
        data = ''

        plainTextstates[0] = plainTextstates[0] ^ IVstate

        for i in range(len(plainTextstates)):
            newState = self.encAES(plainTextstates[i], key)
            data += newState.getData()
            
            if i < len(plainTextstates) - 1:
                plainTextstates[i+1] = plainTextstates[i+1] ^ newState
        
        self.data = Binary(data)

    def decAES_CBC(self, key, IV):
        keySize = len(key)
        cipherTextStates = self.getStates(self.data, keySize)
        IVstate = State(str(IV), keySize)
        data = ''

        for i in range(len(cipherTextStates) - 1, -1, -1):
            newState = self.decAES(cipherTextStates[i], key)
            
            if i == 0:
                data = (newState ^ IVstate).getData() + data
            elif i == len(cipherTextStates) - 1:
                data = self.removePadding((cipherTextStates[i-1] ^ newState).getData())
            else:
                data = (cipherTextStates[i-1] ^ newState).getData() + data
            
        self.data = Binary(data)

    def toHex(self):
        return self.data.toHex()

    def toAscii(self):
        return self.data.toAscii()