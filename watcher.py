import Xlib
import Xlib.display
from enum import Enum
import re
import subprocess


class Watcher:
    def __init__(self, config, w_name=None, w_class=None):
        self.config = config
        self.w_name = w_name
        self.w_class = w_class

    def handle_update(self, new_name, new_class):
        if (self.w_name, self.w_class) == (new_name, new_class):
            return

        for item in self.config:
            item.handle_change((self.w_name, self.w_class), (new_name, new_class))

        self.w_name = new_name
        self.w_class = new_class

        # TODO: Add debug flag to show all changes
        # print('change', self.w_name, self.w_class)

class PropType(Enum):
    NAME = 0
    CLASS = 1


class RuleType(Enum):
    ON_MATCH = 0
    STOPPED_MATCHING = 1


class RuleRegex:
    def __init__(self, regex):
        self.regex = re.compile(regex) if regex else None

    def match(self, haystacks):
        if isinstance(haystacks, str) or haystacks is None:
            haystacks = [haystacks]

        for haystack in haystacks:
            if self.regex is not None and haystack is not None:
                if self.regex.match(haystack) is not None:
                    return True
            elif self.regex is None and haystack is None:
                return True

        return False


class Rule:
    def __init__(self, prop_type, rule_type, regex, cmd):
        self.prop_type = prop_type
        self.rule_type = rule_type
        self.regex = RuleRegex(regex)
        self.cmd = cmd

    def handle_change(self, from_props, to_props):
        will_run = False

        for prop_type in [PropType.NAME, PropType.CLASS]:
            if self.prop_type == prop_type and from_props[prop_type.value] != to_props[prop_type.value]:
                matches_now = self.regex.match(to_props[prop_type.value])
                matched_before = self.regex.match(from_props[prop_type.value])
                if self.rule_type == RuleType.ON_MATCH:
                    if matches_now and not matched_before:
                        will_run = True
                        break
                elif self.rule_type == RuleType.STOPPED_MATCHING:
                    if matched_before and not matches_now:
                        will_run = True
                        break

        if will_run:
            self.run_cmd()

    def run_cmd(self):
        result = subprocess.run(self.cmd.split(), stdout=subprocess.DEVNULL)
        # TODO: show errors when there are errors?
        # Maybe config option to show cmd output?
        # print(result.stdout)


def main():
    # TODO config file
    # TODO && conditions for rules
    # TODO window was fullscreened
    # TODO bsp window state change rules
    config = [
            Rule(PropType.NAME, RuleType.ON_MATCH, None, "polybar-msg cmd hide"),
            Rule(PropType.NAME, RuleType.STOPPED_MATCHING, None, "polybar-msg cmd show"),
            ]

    # Connect to the X server and get the root window
    disp = Xlib.display.Display()
    root = disp.screen().root

    # Listen for _NET_ACTIVE_WINDOW changes
    # this will trigger events when the active window is changed
    root.change_attributes(event_mask=Xlib.X.PropertyChangeMask)

    # Prepare the property names we use so they can be fed into X11 APIs
    NET_ACTIVE_WINDOW = disp.intern_atom('_NET_ACTIVE_WINDOW')
    NET_WM_NAME = disp.intern_atom('_NET_WM_NAME')  # UTF-8
    WM_NAME = disp.intern_atom('WM_NAME')           # Legacy encoding
    WM_CLASS = disp.intern_atom('WM_CLASS')

    # init the watcher with the current focus before we update for the first time
    window = disp.get_input_focus().focus
    window.change_attributes(event_mask=Xlib.X.PropertyChangeMask)
    watcher = Watcher(config, window.get_wm_name(), window.get_wm_class())

    while True:
        # next_event() sleeps until we get an event
        event = disp.next_event()

        if event.atom not in [NET_ACTIVE_WINDOW, NET_WM_NAME, WM_NAME, WM_CLASS]:
            # if its not about the window name or class, who cares
            continue

        window = disp.get_input_focus().focus

        # listen for changes in the focused window's properties
        window.change_attributes(event_mask=Xlib.X.PropertyChangeMask)

        watcher.handle_update(window.get_wm_name(), window.get_wm_class())


if __name__ == "__main__":
    main()
