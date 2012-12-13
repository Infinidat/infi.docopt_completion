import subprocess
import re

class DocoptCompletionException(Exception):
    pass

def strip_usage_line(line):
    # just strip everything that is irrelevant
    line = line.strip()
    for strip_char in "()[]|":
        line = line.replace(strip_char, '')
    line = re.sub('<.*?>', '', line)
    line = re.sub('=.*?( |$)', '= ', line)
    return line

def get_usage(cmd):
    cmd_procecss = subprocess.Popen(cmd + " --help", stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    if cmd_procecss.wait() != 0:
        raise DocoptCompletionException("Command does not exist or command help failed")
    usage_lines = cmd_procecss.stdout.read()
    return usage_lines

def split_usage_lines(usage):
    # splits to two lists of lines: one for "Usage" and one for "Options"
    usage = usage.split("Usage:", 1)[-1]
    usage_and_options = usage.split("Options:", 1)
    if len(usage_and_options) == 1:     # no Options section
        usage_and_options.append("")
    usage, options = usage_and_options
    usage_lines = usage.strip().splitlines()
    options_lines = options.strip().splitlines()
    return usage_lines, options_lines

def parse_option_lines(options_lines):
    def sanitize_line(line):
        line = re.sub('=.*?( |$)', '= ', line)
        return line.replace("'", "'\\''").replace('[', '\\[').replace(']', '\\]').strip().split(None, 1)
    return dict(sanitize_line(line) for line in options_lines)

class CommandParams(object):
    """ contains command arguments and subcommands.
    arguments are optional arguments like "-v", "-h", etc.
    subcommands are optional keywords, like the "status" in "git status".
    subcommands have their own CommandParams instance, so the "status" in "git status" can
    have its own arguments and subcommands.
    This way we can describe commands like "git remote add --fetch" with all the different options at each level """
    def __init__(self):
        self.arguments = []
        self.subcommands = {}
        
    def get_subcommand(self, subcommand):
        return self.subcommands.setdefault(subcommand, CommandParams())

def parse_params(cmd):
    # this function creates a parameter tree for the target docopt tool.
    # a parameter tree is a CommandParams instance, see the documentation of the class
    # this function also returns a second parameter, which is a dictionary of option->option help string
    usage = get_usage(cmd)
    usage_lines, options_lines = split_usage_lines(usage)
    param_tree = CommandParams()
    for line in usage_lines:
        line = strip_usage_line(line)
        args = line.split()[1:]
        current_tree = param_tree
        while len(args) > 0:
            arg = args.pop(0)
            if arg.startswith('-'):
                current_tree.arguments.append(arg)
            else:
                current_tree = current_tree.get_subcommand(arg)
    return param_tree, parse_option_lines(options_lines)

class CompletionGenerator(object):
    """ base class for completion file generators """
    def completion_path_exists(self):
        raise NotImplementedError()       # implemented in subclasses
    
    def get_completion_filepath(self, cmd):
        raise NotImplementedError()       # implemented in subclasses
    
    def get_completion_file_content(self, cmd, param_tree, option_help):
        raise NotImplementedError()       # implemented in subclasses
        
    def generate(self, cmd, param_tree, option_help):
        completion_file_content = self.get_completion_file_content(cmd, param_tree, option_help)
        file_path = self.get_completion_filepath(cmd)
        f = open(file_path, "wb")
        f.write(completion_file_content)
        f.close()
        print "Completion file written to {}".format(file_path)
