#timer functionality implementation

import threading
import time
from pydantic import BaseModel

class TimerArgs(BaseModel):
    minutes: int  # duration in minutes

class Timer:    
    def __init__(self):
        """Initialize the timer."""
        self.is_running = False
        self.timer_thread = None
        self.timer_id = 0
        self.args = None
        self.kwargs = None
        self.duration = 0
    
    def set_timer(self,args: TimerArgs):
        """
        Set a timer for the specified duration.
        
        Args:
            duration: The time in seconds to wait before calling the callback
            callback: The function to call when the timer expires
        """
        # Cancel any existing timer
        if self.is_running:
            self.cancel_timer()
        
        # Set up the new timer
        self.duration = args.minutes * 60  # convert minutes to seconds
        self.is_running = True
        
        # Start the timer thread
        def run():
            # Wait for the specified duration
            time.sleep(self.duration)
            # Call the callback function
            self.callback()
            # Mark timer as not running
            self.is_running = False
        
        self.timer_thread = threading.Thread(target=run)
        self.timer_thread.daemon = True
        self.timer_thread.start()
        print(f"New timer set for {self.duration} seconds.")
    
    def cancel_timer(self):
        """Cancel the currently running timer."""
        if self.is_running:
            self.is_running = False
            # Note: We can't actually stop a thread that's sleeping, but we'll mark it as canceled
            if self.timer_thread and self.timer_thread.is_alive():
                print("Timer canceled.")
            self.is_running = False

    def callback(self):
        """Callback function to be called when the timer expires."""
        print("Timer expired!")

TIMER_TOOL = Timer()