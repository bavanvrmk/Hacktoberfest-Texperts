"""
Event Bus Module (Thread-Safe Pub/Sub)
Connects Spotlight UI, Orchestrator, OS Sandbox, AR Overlay, and ROI Analytics.
"""

import threading
from typing import Callable, Dict, List, Any

class EventBus:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(EventBus, cls).__new__(cls)
                cls._instance._subscribers: Dict[str, List[Callable]] = {}
                cls._instance._sub_lock = threading.Lock()
            return cls._instance

    def subscribe(self, event_name: str, callback: Callable[[Any], None]):
        """Subscribe a listener callback to an event."""
        with self._sub_lock:
            if event_name not in self._subscribers:
                self._subscribers[event_name] = []
            if callback not in self._subscribers[event_name]:
                self._subscribers[event_name].append(callback)

    def unsubscribe(self, event_name: str, callback: Callable[[Any], None]):
        """Unsubscribe a listener from an event."""
        with self._sub_lock:
            if event_name in self._subscribers and callback in self._subscribers[event_name]:
                self._subscribers[event_name].remove(callback)

    def emit(self, event_name: str, data: Any = None):
        """Emit an event to all subscribed listeners."""
        with self._sub_lock:
            callbacks = list(self._subscribers.get(event_name, []))
            
        for callback in callbacks:
            try:
                callback(data)
            except Exception as e:
                print(f"[EventBus Error] Exception in callback for event '{event_name}': {e}")

# Global singleton event bus
event_bus = EventBus()

# Event Constants
EVENT_TASK_START = "task:start"
EVENT_PROGRESS = "task:progress"
EVENT_PII_REDACTED = "task:pii_redacted"
EVENT_GROUNDING_COMPLETED = "task:grounding_completed"
EVENT_OVERLAY_DRAW = "ui:overlay_draw"
EVENT_ACTION_EXECUTED = "task:action_executed"
EVENT_STATE_VERIFIED = "task:state_verified"
EVENT_SELF_HEALING = "task:self_healing"
EVENT_TASK_SUCCESS = "task:success"
EVENT_TASK_FAILED = "task:failed"
EVENT_TOAST_SHOW = "ui:toast_show"
EVENT_VISUAL_THOUGHT = "task:visual_thought"
