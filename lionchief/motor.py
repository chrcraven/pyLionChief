"""
Copyright (c) Jordan Maxwell, All Rights Reserved.
See LICENSE file in the project root for full license information.
"""

import asyncio
from lionchief.protocol import *

class LionChiefMotorController(object):
    """
    Class for controlling the motor functions of a LionChief train
    """

    def __init__(self, train: object) -> None:
        """
        Initialize a LionChiefMotorController object.

        Args:
            train (object): The train object.
        """

        self.train = train
        self._current_speed = 0  # Track current speed

    async def set_speed(self, speed: int) -> None:
        """
        Set the speed of the train.

        Args:
            speed (int): The speed of the train (0-100, where 0 is stopped and 100 is maximum speed).
        """
        self._current_speed = speed
        await self.train.send_train_command(LionChiefBluetoothCommands.SetSpeed, [speed])

    async def set_movement_direction(self, forward: bool) -> None:
        """
        Set the state of the train's movement direction.

        Args:
            state (bool): Movement direction value (True for forward, False for reverse).
        """
        await self.train.send_train_command(LionChiefBluetoothCommands.SetMovementDirection, [0x01 if forward else 0x02])

    async def gradual_speed_change(self, target_speed: int, step: int = 5, delay: float = 0.2) -> None:
        """
        Gradually change speed from current speed to target speed.

        Args:
            target_speed (int): The target speed (0-100).
            step (int): How much to change speed each step (default: 5).
            delay (float): Delay in seconds between each step (default: 0.2).
        """
        if target_speed < 0 or target_speed > 100:
            raise ValueError(f"Target speed must be between 0 and 100 (got {target_speed})")

        if step <= 0:
            raise ValueError(f"Step must be positive (got {step})")

        current = self._current_speed

        if current < target_speed:
            # Speed up
            while current < target_speed:
                current = min(current + step, target_speed)
                await self.set_speed(current)
                if current < target_speed:  # Don't delay after final step
                    await asyncio.sleep(delay)
        elif current > target_speed:
            # Slow down
            while current > target_speed:
                current = max(current - step, target_speed)
                await self.set_speed(current)
                if current > target_speed:  # Don't delay after final step
                    await asyncio.sleep(delay)

    async def stop(self) -> None:
        """
        Stop the train (set speed to 0).
        """
        await self.set_speed(0)
