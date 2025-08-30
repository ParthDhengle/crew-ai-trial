import sys
import uiautomation as auto
if sys.platform == 'darwin':
    import pyatspi

def get_selected_text():
    if sys.platform == 'win32':
        try:
            control = auto.GetFocusedControl()
            return control.GetSelectedText() if hasattr(control, 'GetSelectedText') else ""
        except:
            return ""
    elif sys.platform == 'darwin':
        try:
            accessible = pyatspi.Registry.getDesktop(0).getAccessibleAtPoint(*pyatspi.getMousePosition())
            if accessible and accessible.getState().contains(pyatspi.STATE_FOCUSED):
                text_iface = accessible.getText()
                return text_iface.getText(text_iface.caretOffset, text_iface.characterCount) if text_iface else ""
        except:
            return ""
    return ""

def get_selection_pos():
    if sys.platform == 'win32':
        try:
            control = auto.GetFocusedControl()
            rect = control.BoundingRectangle
            return auto.QPoint(rect.right, rect.top - 30)
        except:
            return auto.QCursor.pos()
    elif sys.platform == 'darwin':
        return auto.QPoint(*pyatspi.getMousePosition()) + auto.QPoint(10, -20)  # Adjust offset
    return auto.QCursor.pos()

def setup_event_listener(callback):
    if sys.platform == 'win32':
        class Handler(auto.UIAEventHandler):
            def HandlePropertyChangedEvent(self, sender, propertyId, newValue):
                if propertyId in [auto.PropertyId.ValueValuePropertyId, auto.PropertyId.SelectionSelectionPropertyId]:
                    callback()
        handler = Handler()
        auto.uiaClient.AddPropertyChangedEventHandler(auto.GetRootControl(), auto.TreeScope.Subtree, None, handler,
                                                      [auto.PropertyId.ValueValuePropertyId, auto.PropertyId.SelectionSelectionPropertyId])
    elif sys.platform == 'darwin':
        def event_cb(event):
            if event.type in (pyatspi.TEXT_CARET_MOVED, pyatspi.TEXT_SELECTION_CHANGED, pyatspi.FOCUS):
                callback()
        pyatspi.Registry.registerEventListener(event_cb, pyatspi.TEXT_CARET_MOVED, pyatspi.TEXT_SELECTION_CHANGED, pyatspi.FOCUS)