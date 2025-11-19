"""
Copyright (c) Jordan Maxwell, All Rights Reserved.
See LICENSE file in the project root for full license information.
"""

import sys
sys.path.insert(0, '../')

from lionchief.connection import discover_train
from time import sleep
from bleak import BleakError
import asyncio
import inspect
import ast
import platform

# Platform-aware Unicode support
# Windows cmd.exe may not support Unicode properly
def _supports_unicode() -> bool:
    """Check if the terminal supports Unicode characters"""
    if platform.system() == 'Windows':
        # Windows Terminal and PowerShell support Unicode, cmd.exe may not
        # Check if we're in a modern terminal
        try:
            import codecs
            return sys.stdout.encoding.lower().startswith('utf')
        except:
            return False
    return True

_UNICODE_SUPPORT = _supports_unicode()

# Cross-platform symbols
if _UNICODE_SUPPORT:
    CHECK_MARK = '✓'
    CROSS_MARK = '❌'
    H_LINE = '═'
    TOP_LEFT = '┌'
    TOP_RIGHT = '┐'
    BOTTOM_LEFT = '└'
    BOTTOM_RIGHT = '┘'
    V_LINE = '│'
else:
    # ASCII fallbacks for Windows cmd.exe
    CHECK_MARK = '[OK]'
    CROSS_MARK = '[X]'
    H_LINE = '='
    TOP_LEFT = '+'
    TOP_RIGHT = '+'
    BOTTOM_LEFT = '+'
    BOTTOM_RIGHT = '+'
    V_LINE = '|'

# Help documentation for all available commands
# Box drawing characters will be replaced at runtime for Windows compatibility
HELP_TEXT_TEMPLATE = """
┌─────────────────────────────────────────────────────────────────────────────┐
│                     LionChief Train Control CLI                             │
│                                                                             │
│  Command Format: <component>,<method>,<arg1>,<arg2>,...                    │
└─────────────────────────────────────────────────────────────────────────────┘

═══════════════════════════════════════════════════════════════════════════════
MOTOR COMMANDS
═══════════════════════════════════════════════════════════════════════════════

  motor,set_speed,<speed>
    Set the train's speed
    Arguments:
      speed (int): Speed value (0-255, where 0 is stopped, 255 is max speed)
    Examples:
      motor,set_speed,0         # Stop the train
      motor,set_speed,100       # Set to medium speed
      motor,set_speed,255       # Set to maximum speed

  motor,set_movement_direction,<forward>
    Set the train's movement direction
    Arguments:
      forward (bool): True for forward, False for reverse
    Examples:
      motor,set_movement_direction,True    # Set to forward
      motor,set_movement_direction,False   # Set to reverse

═══════════════════════════════════════════════════════════════════════════════
LIGHTING COMMANDS
═══════════════════════════════════════════════════════════════════════════════

  lighting,set_lights,<state>
    Turn the train's lights on or off
    Arguments:
      state (bool): True to turn lights on, False to turn off
    Examples:
      lighting,set_lights,True    # Turn lights on
      lighting,set_lights,False   # Turn lights off

═══════════════════════════════════════════════════════════════════════════════
SOUND COMMANDS
═══════════════════════════════════════════════════════════════════════════════

  sound,set_horn,<state>
    Turn the train's horn on or off
    Arguments:
      state (bool): True to sound horn, False to stop
    Examples:
      sound,set_horn,True     # Sound the horn
      sound,set_horn,False    # Stop the horn

  sound,set_bell,<state>
    Turn the train's bell on or off
    Arguments:
      state (bool): True to ring bell, False to stop
    Examples:
      sound,set_bell,True     # Ring the bell
      sound,set_bell,False    # Stop the bell

  sound,set_steam_volume,<volume>
    Set the steam sound volume
    Arguments:
      volume (int): Volume level (0-4, where 0 is muted, 4 is loudest)
    Examples:
      sound,set_steam_volume,0    # Mute steam sounds
      sound,set_steam_volume,2    # Set to medium volume
      sound,set_steam_volume,4    # Set to maximum volume

  sound,set_horn_pitch,<pitch>
    Set the horn pitch
    Arguments:
      pitch (int): Pitch level (0-4)
    Examples:
      sound,set_horn_pitch,0    # Lowest pitch
      sound,set_horn_pitch,2    # Medium pitch
      sound,set_horn_pitch,4    # Highest pitch

  sound,set_bell_pitch,<pitch>
    Set the bell pitch
    Arguments:
      pitch (int): Pitch level (0-4)
    Examples:
      sound,set_bell_pitch,0    # Lowest pitch
      sound,set_bell_pitch,4    # Highest pitch

  sound,set_voice_line_volume,<volume>
    Set the voice line volume
    Arguments:
      volume (int): Volume level (0-4, where 0 is muted, 4 is loudest)
    Examples:
      sound,set_voice_line_volume,3    # Set voice to high volume

  sound,set_engine_volume,<volume>
    Set the engine sound volume
    Arguments:
      volume (int): Volume level (0-4, where 0 is muted, 4 is loudest)
    Examples:
      sound,set_engine_volume,2    # Set engine to medium volume

  sound,play_voice_line
    Play a random voice line
    Arguments:
      None
    Examples:
      sound,play_voice_line    # Play a voice line

═══════════════════════════════════════════════════════════════════════════════
CONNECTION COMMANDS
═══════════════════════════════════════════════════════════════════════════════

  connection,disconnect
    Disconnect from the train
    Arguments:
      None
    Examples:
      connection,disconnect    # Disconnect from train

═══════════════════════════════════════════════════════════════════════════════
UTILITY COMMANDS
═══════════════════════════════════════════════════════════════════════════════

  help
    Display this help message

  exit or quit
    Exit the CLI application

═══════════════════════════════════════════════════════════════════════════════
QUICK START EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

  1. Start the train moving forward at medium speed:
     motor,set_movement_direction,True
     motor,set_speed,128

  2. Ring the bell and turn on lights:
     sound,set_bell,True
     lighting,set_lights,True

  3. Stop the train and turn everything off:
     motor,set_speed,0
     sound,set_bell,False
     sound,set_horn,False
     lighting,set_lights,False

  4. Adjust all volume levels:
     sound,set_steam_volume,3
     sound,set_engine_volume,3
     sound,set_voice_line_volume,4

═══════════════════════════════════════════════════════════════════════════════

"""

def _get_help_text() -> str:
    """Get help text with platform-appropriate box drawing characters"""
    if _UNICODE_SUPPORT:
        return HELP_TEXT_TEMPLATE
    else:
        # Replace Unicode box drawing characters with ASCII equivalents for Windows cmd.exe
        text = HELP_TEXT_TEMPLATE
        text = text.replace('┌', '+').replace('┐', '+')
        text = text.replace('└', '+').replace('┘', '+')
        text = text.replace('│', '|')
        text = text.replace('─', '-')
        text = text.replace('═', '=')
        return text

def cast_argument(argument, arg_type):
    try:
        return ast.literal_eval(argument)
    except ValueError:
        return arg_type(argument)

async def execute_service_command(service_component: object, func_name: str, arguments: list) -> None:
    if not hasattr(service_component, func_name):
        raise ValueError("Function name (%s) not found" % func_name)

    func_inst = getattr(service_component, func_name)
    argspec = inspect.getfullargspec(func_inst)
    params = argspec.args[1:]  # Ignore "self" parameter
    
    if len(arguments) < len(params):
        raise ValueError("Incorrect number of arguments supplied. Expected %s, got %s" % (len(params), len(arguments)))

    args = []
    for param, arg in zip(params, arguments):
        arg_type = argspec.annotations.get(param, str)
        cast_arg = cast_argument(arg, arg_type)
        args.append(cast_arg)

    result = None
    if inspect.iscoroutinefunction(func_inst):
        result = await func_inst(*args)
    else:
        result = func_inst(*args)

    if result != None:
        print(result)

def get_service_command_args(input_list: list) -> list:
    if len(input_list) > 2:
        # Strip whitespace from each argument
        return [arg.strip() for arg in input_list[2:]]
    else:
        return []

async def main() -> None:
    print("\n" + "="*80)
    print("LionChief Train Control CLI".center(80))
    print("="*80)
    print("\nScanning for trains... (Press Ctrl+C to cancel)\n")

    d = await discover_train(retry=True)
    try:
        await d.connect()
        print("\n" + "="*80)
        print("Connected to train!".center(80))
        print("="*80)
        print("\nType 'help' for available commands, 'exit' or 'quit' to exit\n")

        while d.train.is_connected:
            command = input("LionChief> ").strip()

            # Handle empty input
            if not command:
                continue

            # Handle utility commands
            if command.lower() in ['help', '?']:
                print(_get_help_text())
                continue

            if command.lower() in ['exit', 'quit', 'q']:
                print("\nExiting...")
                break

            # Parse command
            command_parts = command.split(',')
            if len(command_parts) < 2:
                print(f'{CROSS_MARK} Invalid command format.')
                print('   Format: <component>,<method>,<arg1>,<arg2>,...')
                print('   Type "help" for more information.')
                continue

            service_component_name = command_parts[0].strip()
            service_component_method = command_parts[1].strip()
            service_command_parts = get_service_command_args(command_parts)

            try:
                if service_component_name == "connection":
                    await execute_service_command(d, service_component_method, service_command_parts)
                    print(f"{CHECK_MARK} Command executed successfully")
                elif service_component_name == "motor":
                    await execute_service_command(d.motor, service_component_method, service_command_parts)
                    print(f"{CHECK_MARK} Command executed successfully")
                elif service_component_name == "sound":
                    await execute_service_command(d.sound, service_component_method, service_command_parts)
                    print(f"{CHECK_MARK} Command executed successfully")
                elif service_component_name == "lighting":
                    await execute_service_command(d.lighting, service_component_method, service_command_parts)
                    print(f"{CHECK_MARK} Command executed successfully")
                else:
                    print(f'{CROSS_MARK} Unknown component: {service_component_name}')
                    print('   Valid components: connection, motor, sound, lighting')
            except ValueError as err:
                print(f"{CROSS_MARK} Error: {err}")
            except SyntaxError as err:
                print(f'{CROSS_MARK} Invalid arguments. Check your inputs')
            except AttributeError as err:
                print(f'{CROSS_MARK} Unknown method: {service_component_method}')
                print(f'   Type "help" to see available commands for {service_component_name}')
            except Exception as err:
                print(f'{CROSS_MARK} Unexpected error: {err}')

    except OSError as err:
        print(f"\n{CROSS_MARK} Discovery failed due to operating system: {err}")
    except BleakError as err:
        print(f"\n{CROSS_MARK} Discovery failed due to Bleak: {err}")
    except KeyboardInterrupt as err:
        print("\n\nInterrupted by user.")
    finally:
        print("\n" + "="*80)
        print("Shutting down...".center(80))
        print("="*80)
        if d and d.train:
            await d.disconnect()
        print("\nGoodbye!\n")

if __name__ == "__main__":
    asyncio.run(main())
