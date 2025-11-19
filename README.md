# PyLionChief

PyLionChief is an open-source project that aims to provide Python access to the Lionel's LionChief line of trains.

## Platform Support

PyLionChief is cross-platform and works on:
- **Linux** (including Raspberry Pi)
- **Windows** (Windows 10/11 with Bluetooth LE support)
- **macOS** (with Bluetooth support)

### Platform-Specific Requirements

#### Raspberry Pi (Recommended)
For enhanced reliability on Raspberry Pi, install the optional dependencies:
```bash
pip install -r requirements-rpi.txt
```

This enables D-Bus adapter cleanup to prevent "Operation already in progress" errors that can occur with BlueZ on Raspberry Pi systems.

#### Windows
- Requires Windows 10 or later with Bluetooth LE support
- Administrator privileges may be required for Bluetooth access
- For best terminal experience, use Windows Terminal or PowerShell (Unicode support)

#### macOS
- Requires Bluetooth permissions for the terminal/Python application
- May prompt for Bluetooth access on first run

#### Linux (General)
- Requires BlueZ Bluetooth stack
- User must be in the `bluetooth` group or have appropriate permissions
- Install system Bluetooth tools: `sudo apt-get install bluetooth bluez`

## Installation

PyLionChief can be installed using `pip`, or by downloading the source code and running the `setup.py` script.

### Installing with pip

To install PyLionChief using `pip`, simply run:

```
pip install pylionchief
```

### Installing from source

To install PyLionChief from source, follow these steps:

1. Download the source code from the [GitHub repository](https://github.com/thetestgame/pyLionChief).
2. Extract the contents of the archive to a directory of your choice.
3. Navigate to the directory containing the `setup.py` script.
4. Run the following command:

```
python setup.py install
```

## Examples

PyLionChief comes with a few examples to help users get started. These examples can be found under the `examples` directory in the repository root.

## License
PyLionChief is released under the MIT license. See the LICENSE file for more details.
