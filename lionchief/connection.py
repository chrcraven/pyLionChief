"""
Copyright (c) Jordan Maxwell, All Rights Reserved.
See LICENSE file in the project root for full license information.
"""

import asyncio
import logging
import os
from bleak import BleakScanner, BleakClient
from bleak.exc import BleakError

from lionchief.protocol import *
from lionchief.motor import LionChiefMotorController
from lionchief.sound import LionChiefSoundController
from lionchief.lighting import LionChiefLightingController

# Global lock to prevent concurrent BLE scanning operations
# This prevents "Operation already in progress" errors at the BlueZ level
_scan_lock = asyncio.Lock()

# Try to import pydbus for Raspberry Pi D-Bus cleanup
# This is optional and only used on Raspberry Pi
try:
    from pydbus import SystemBus
    _PYDBUS_AVAILABLE = True
except ImportError:
    _PYDBUS_AVAILABLE = False

def _is_raspberry_pi() -> bool:
    """
    Detect if running on a Raspberry Pi.

    Returns:
        True if running on Raspberry Pi, False otherwise
    """
    try:
        # Check for Raspberry Pi specific files
        if os.path.exists('/sys/firmware/devicetree/base/model'):
            with open('/sys/firmware/devicetree/base/model', 'r') as f:
                model = f.read().lower()
                if 'raspberry pi' in model:
                    return True

        # Fallback: check for BCM chip in /proc/cpuinfo
        if os.path.exists('/proc/cpuinfo'):
            with open('/proc/cpuinfo', 'r') as f:
                cpuinfo = f.read().lower()
                if 'bcm' in cpuinfo and 'raspberry' in cpuinfo:
                    return True
    except Exception:
        pass

    return False

# Cache the platform detection result
_IS_RASPBERRY_PI = _is_raspberry_pi()

# Log platform detection info at module load
if _IS_RASPBERRY_PI:
    logging.debug("Raspberry Pi detected - BlueZ adapter cleanup enabled")
    if not _PYDBUS_AVAILABLE:
        logging.info("pydbus not available - install with 'pip install pydbus' for enhanced Raspberry Pi BLE reliability")
else:
    logging.debug("Not running on Raspberry Pi - BlueZ adapter cleanup disabled")

async def _ensure_clean_adapter_state(adapter_name: str = 'hci0') -> None:
    """
    Ensure Bluetooth adapter is not in discovery mode before scanning.

    This function is specifically designed for Raspberry Pi systems where
    BlueZ can get stuck in discovery mode, causing "Operation already in progress" errors.

    On non-Raspberry Pi systems, this function does nothing.

    Args:
        adapter_name (str): The Bluetooth adapter name (default: 'hci0')
    """
    # Only attempt cleanup on Raspberry Pi with pydbus available
    if not _IS_RASPBERRY_PI or not _PYDBUS_AVAILABLE:
        return

    try:
        bus = SystemBus()
        adapter_path = f'/org/bluez/{adapter_name}'
        adapter = bus.get('org.bluez', adapter_path)

        # Check if discovery is active
        if adapter.Discovering:
            logging.info(f"Stopping active discovery on {adapter_name}...")
            try:
                adapter.StopDiscovery()
                await asyncio.sleep(0.5)  # Give BlueZ time to clean up
                logging.debug(f"Successfully stopped discovery on {adapter_name}")
            except Exception as e:
                logging.debug(f"Could not stop discovery: {e}")
                # Continue anyway - not critical
    except Exception as e:
        # D-Bus errors are not critical - the retry logic will handle it
        logging.debug(f"Could not check adapter state via D-Bus: {e}")

class LionChiefConnection(object):
    """
    Represents a connection to a LionChief train.
    """

    LionChiefServiceId = 'e20a39f4-73f5-4bc4-a12f-17d1ad07a961'

    def __init__(self, profile: str, manufacturer_data):
        """
        Initialize a LionChiefConnection object.

        Args:
            profile (str): The BLE profile of the train.
            manufacturer_data: The manufacturer data of the train.
        """
        
        self.profile = profile
        self.train = None
        self.manufacturer_data = manufacturer_data

        self.motor = LionChiefMotorController(self)
        self.sound = LionChiefSoundController(self)
        self.lighting = LionChiefLightingController(self)

    async def connect(self, silent: bool = False) -> None:
        """
        Connect to the LionChief train using BLE.
        """

        timeout = 0.0
        self.train = BleakClient(self.profile)
        await self.train.connect()

    async def disconnect(self, silent: bool = False) -> None:
        """
        Disconnect from the train.
        """

        if not self.train.is_connected:
            return

        logging.info("Disconnecting from train...")
        await self.send_train_command(LionChiefBluetoothCommands.Disconnect, [0, 0])
        await self.train.disconnect()

    async def send_train_command(self, command_id: int, values: list = []) -> None:
        """
        Send a command to the train.

        Args:
            command_id (int): The ID of the command.
            values (list): The values to be sent along with the command.
        """
        values.insert(0, command_id)

        checksum = 256
        for v in values:
            checksum -= v

        while checksum < 0:
            checksum += 256

        values.insert(0, 0)
        values.append(checksum)

        command = bytes(values)
        logging.debug('Sending command: %s' % command.hex())
        await self.train.write_gatt_char(LionChiefBluetoothCharacteristics.LionChiefWriteCharacteristic, command)

async def discover_trains(retry: bool = False, max_retries: int = 10) -> list:
    """
    Scans for nearby Bluetooth devices with the LionChief service id and returns if found. If retry is True, the function will
    converted to a DroidConnection and added to a list to return. If retry is False, the function will out after a set
    period of time and return without discovering any trains.

    Args:
        retry (bool): whether or not to continue scanning until a device is found or the function is interrupted
        max_retries (int): maximum number of scan retry attempts (default: 10)

    Returns:
        a list of LionChiefConnection objects representing the discovered train Bluetooth devices if any. Otherwise an empty list

    Note:
        Uses a global lock to prevent concurrent BLE scans, which can cause "Operation already in progress"
        errors at the BlueZ level on Linux systems (especially Raspberry Pi).

        On Raspberry Pi systems with pydbus installed, this function will also attempt to clean up
        any stuck discovery state via D-Bus before scanning.
    """

    train_connections = []
    retry_count = 0
    backoff_delay = 1.0  # Start with 1 second delay

    # On Raspberry Pi, ensure adapter is not stuck in discovery mode
    # This is a no-op on other platforms
    await _ensure_clean_adapter_state()

    while True:
        # Acquire lock to prevent concurrent BLE scanning operations
        # This is critical for preventing BlueZ "Operation already in progress" errors
        async with _scan_lock:
            try:
                # Scan for devices with the LionChief service UUID
                logging.debug("Starting BLE scan for LionChief trains...")
                devices = await BleakScanner.discover(
                    return_adv=True,
                    service_uuids=[LionChiefConnection.LionChiefServiceId],
                    timeout=5.0
                )

                if len(devices) == 0:
                    if retry and retry_count < max_retries:
                        retry_count += 1
                        logging.warning(f"No trains discovered. Retrying ({retry_count}/{max_retries})...")
                        await asyncio.sleep(backoff_delay)
                        # Exponential backoff, capped at 8 seconds
                        backoff_delay = min(backoff_delay * 1.5, 8.0)
                        continue
                    else:
                        logging.error("Train discovery failed - no devices found.")
                        break
                else:
                    # Process discovered trains
                    for ble_device, advertising_data in devices.values():
                        logging.info(f"Train successfully discovered: [ {ble_device} ]")
                        train_connections.append(LionChiefConnection(ble_device, advertising_data.manufacturer_data))
                    break

            except BleakError as e:
                error_msg = str(e).lower()

                # Handle "Operation already in progress" error specifically
                if "operation already in progress" in error_msg or "busy" in error_msg:
                    if retry and retry_count < max_retries:
                        retry_count += 1
                        logging.warning(f"Bluetooth adapter busy (operation already in progress). Waiting {backoff_delay:.1f}s before retry ({retry_count}/{max_retries})...")
                        await asyncio.sleep(backoff_delay)
                        # Exponential backoff, capped at 10 seconds for adapter busy errors
                        backoff_delay = min(backoff_delay * 2.0, 10.0)
                        continue
                    else:
                        logging.error(f"BLE scan failed: {e}")
                        break
                else:
                    # Handle other BleakErrors
                    if retry and retry_count < max_retries:
                        retry_count += 1
                        logging.warning(f"BLE error occurred: {e}. Retrying ({retry_count}/{max_retries})...")
                        await asyncio.sleep(backoff_delay)
                        backoff_delay = min(backoff_delay * 1.5, 8.0)
                        continue
                    else:
                        logging.error(f"BLE scan failed: {e}")
                        break

            except Exception as e:
                # Catch any other unexpected errors
                logging.error(f"Unexpected error during train discovery: {e}")
                if retry and retry_count < max_retries:
                    retry_count += 1
                    logging.warning(f"Retrying after unexpected error ({retry_count}/{max_retries})...")
                    await asyncio.sleep(backoff_delay)
                    backoff_delay = min(backoff_delay * 1.5, 8.0)
                    continue
                else:
                    break

        # Small delay after releasing lock to allow BlueZ to fully clean up
        # This helps prevent residual state issues on Raspberry Pi
        await asyncio.sleep(0.1)

    return train_connections

async def discover_train(retry: bool = False, max_retries: int = 10) -> LionChiefConnection:
    """
    Scans for nearby Bluetooth devices with the LionChief service id and returns if found. If retry is True, the function will
    continue scanning until it finds a device or is interrupted. If retry is False, the function will time out after a
    set period of time and return without discovering a device.

    Args:
        retry (bool): whether or not to continue scanning until a device is found or the function is interrupted
        max_retries (int): maximum number of scan retry attempts (default: 10)

    Returns:
        a LionChiefConnection object representing the discovered train Bluetooth device if any. Otherwise None
    """

    discovered_trains = await discover_trains(retry, max_retries)
    return None if len(discovered_trains) == 0 else discovered_trains[0]