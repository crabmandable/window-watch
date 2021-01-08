import Xlib
import Xlib.display
from time import sleep
from enum import Enum
import re
import subprocess

SLEEP_DUR = 0.1


class Watcher:
    def __init__(self, config):
        self.config = config
        self.w_name = None
        self.w_class = None

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
                if self.rule_type == RuleType.ON_MATCH and self.regex.match(to_props[prop_type.value]):
                    will_run = True
                elif self.rule_type == RuleType.STOPPED_MATCHING and self.regex.match(from_props[prop_type.value]):
                    will_run = True

        if will_run:
            self.run_cmd()

    def run_cmd(self):
        result = subprocess.run(self.cmd.split(), stdout=subprocess.DEVNULL)
        # TODO: show errors when there are errors?
        # Maybe config option to show cmd output?
        # print(result.stdout)

def main():
    disp = Xlib.display.Display()

    # TODO config file
    config = [
            Rule(PropType.NAME, RuleType.ON_MATCH, None, "polybar-msg cmd hide"),
            Rule(PropType.NAME, RuleType.STOPPED_MATCHING, None, "polybar-msg cmd show"),
            ]

    watcher = Watcher(config)
    while True:
        window = disp.get_input_focus().focus
        watcher.handle_update(window.get_wm_name(), window.get_wm_class())
        sleep(SLEEP_DUR)


if __name__ == "__main__":
    main()
