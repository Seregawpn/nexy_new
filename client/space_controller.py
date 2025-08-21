import Quartz
import time
from typing import Callable
from context_detector import ContextDetector

class SpaceController:
    """
    Monitors spacebar events at the OS level to control the assistant.
    It distinguishes between long and short presses to activate, deactivate, or interrupt.
    """
    def __init__(self, loop, event_queue):
        self.loop = loop
        self.event_queue = event_queue
        self.context_detector = ContextDetector()
        
        self.press_start_time = 0
        self.long_press_threshold = 0.5  # 500ms for a long press
        self.short_press_threshold = 0.3 # 300ms for a short press
        self.is_space_down = False

    def start_monitoring(self):
        """
        Creates and runs a Quartz Event Tap to listen for keyboard events.
        This is the core of the push-to-talk functionality.
        """
        event_mask = (1 << Quartz.kCGEventKeyDown) | (1 << Quartz.kCGEventKeyUp)
        
        # The callback function that will be executed by the Event Tap
        def event_tap_callback(proxy, event_type, event, refcon):
            keycode = Quartz.CGEventGetIntegerValueField(event, Quartz.kCGKeyboardEventKeycode)
            
            # Spacebar keycode is 49
            if keycode == 49:
                if self.context_detector.is_text_field_focused():
                    # If a text field is focused, do not interfere
                    return event

                if event_type == Quartz.kCGEventKeyDown:
                    if not self.is_space_down:
                        self.is_space_down = True
                        self.press_start_time = time.time()
                        self.loop.call_soon_threadsafe(self.event_queue.put_nowait, "start_recording")
                
                elif event_type == Quartz.kCGEventKeyUp:
                    if self.is_space_down:
                        self.is_space_down = False
                        press_duration = time.time() - self.press_start_time
                        
                        if press_duration >= self.long_press_threshold:
                            # Long press release: stop recording
                            self.loop.call_soon_threadsafe(self.event_queue.put_nowait, "stop_recording")
                        elif press_duration < self.short_press_threshold:
                            # Short press: interrupt or cancel
                            self.loop.call_soon_threadsafe(self.event_queue.put_nowait, "interrupt_or_cancel")

            return event

        # Create the Event Tap
        event_tap = Quartz.CGEventTapCreate(
            Quartz.kCGSessionEventTap,
            Quartz.kCGHeadInsertEventTap,
            Quartz.kCGEventTapOptionDefault,
            event_mask,
            event_tap_callback,
            None
        )

        if not event_tap:
            print("Failed to create event tap. Make sure you have Accessibility permissions.")
            return

        # Create a run loop source and add it to the current run loop
        run_loop_source = Quartz.CFMachPortCreateRunLoopSource(None, event_tap, 0)
        Quartz.CFRunLoopAddSource(Quartz.CFRunLoopGetCurrent(), run_loop_source, Quartz.kCFRunLoopCommonModes)
        Quartz.CGEventTapEnable(event_tap, True)
        Quartz.CFRunLoopRun()

    def run_in_thread(self):
        """
        Runs the monitoring in a separate thread to avoid blocking the main asyncio loop.
        """
        import threading
        thread = threading.Thread(target=self.start_monitoring, daemon=True)
        thread.start()
