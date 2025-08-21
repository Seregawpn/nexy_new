import Quartz

class ContextDetector:
    def is_text_field_focused(self) -> bool:
        """
        Checks if the current focus is on a text field.
        This is crucial to prevent the assistant from activating when the user is typing.
        """
        try:
            # Get the UI element that currently has focus system-wide
            system_wide_element = Quartz.AXUIElementCreateSystemWide()
            focused_element = Quartz.AXUIElementCopyAttributeValue(
                system_wide_element,
                Quartz.kAXFocusedUIElementAttribute
            )

            if focused_element:
                # Check if the focused element is editable (e.g., a text field, search bar)
                is_editable = Quartz.AXUIElementCopyAttributeValue(
                    focused_element,
                    Quartz.kAXEditableAttribute
                )
                return bool(is_editable)

        except Exception as e:
            # If there's any issue, assume it's not a text field to be safe
            print(f"Could not determine context: {e}")
            return False
            
        return False
