import Xlib
import Xlib.display
from enum import Enum
import re
import subprocess


class Watcher:
    def __init__(self, rules, w_name=None, w_class=None):
        self.rules = rules
        self.w_name = w_name
        self.w_class = w_class

    def handle_update(self, new_name, new_class):
        if (self.w_name, self.w_class) == (new_name, new_class):
            return

        for rule in self.rules:
            if rule.handle_change((self.w_name, self.w_class), (new_name, new_class)):
                rule.run_cmd()


        self.w_name = new_name
        self.w_class = new_class

        # TODO: Add debug flag to show all changes
        # print('change', self.w_name, self.w_class)

class PropType(Enum):
    NAME = 0
    CLASS = 1


class ConditionType(Enum):
    ON_MATCH = 0
    STOPPED_MATCHING = 1


class RuleType(Enum):
    ANY = 0
    ALL = 0

class ConditionRegex:
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
    def __init__(self, rule_type, conditions, cmd):
        self.rule_type = rule_type
        self.cmd = cmd
        self.conditions = conditions

    def handle_change(self, from_props, to_props):
        met = [c.handle_change(from_props, to_props) for c in self.conditions]
        if self.rule_type == RuleType.ANY:
            return any(met)
        elif self.rule_type == RuleType.ALL:
            return all(met)
        else:
            raise NotImplemented("Unsupported RuleType")


    def run_cmd(self):
        # TODO: useful debug prints should be configurable
        # print('decided a rule triggered')
        # print('running', self.cmd)

        result = subprocess.run(self.cmd.split(), stdout=subprocess.DEVNULL)
        # TODO: show errors when there are errors?
        # Maybe config option to show cmd output?
        # print(result.stdout)


class Condition:
    def __init__(self, prop_type, rule_type, regex):
        self.prop_type = prop_type
        self.rule_type = rule_type
        self.regex = ConditionRegex(regex)

    def handle_change(self, from_props, to_props):
        '''
        Returns True/False depending on if the condition is met
        '''
        for prop_type in [PropType.NAME, PropType.CLASS]:
            if self.prop_type == prop_type and from_props[prop_type.value] != to_props[prop_type.value]:
                matches_now = self.regex.match(to_props[prop_type.value])
                matched_before = self.regex.match(from_props[prop_type.value])
                if self.rule_type == ConditionType.ON_MATCH:
                    if matches_now and not matched_before:
                        return True
                elif self.rule_type == ConditionType.STOPPED_MATCHING:
                    if matched_before and not matches_now:
                        return True

        return False


def main():
    # TODO config file
    # TODO && conditions for rules
    # TODO window was fullscreened
    # TODO bsp window state change rules
    config = [
            Rule(RuleType.ANY, [Condition(PropType.NAME, ConditionType.ON_MATCH, None)], "polybar-msg cmd hide"),
            Rule(RuleType.ANY, [Condition(PropType.NAME, ConditionType.STOPPED_MATCHING, None)], "polybar-msg cmd show"),
            Rule(RuleType.ANY, [Condition(PropType.NAME, ConditionType.ON_MATCH, ".*VIM$")], "/home/crab/.config/bspwm/recolor.sh #3DAF6F"),
            Rule(RuleType.ANY, [Condition(PropType.NAME, ConditionType.STOPPED_MATCHING, ".*VIM$")], "/home/crab/.config/bspwm/recolor.sh back"),
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
