from __future__ import print_function
import subprocess
import re

class DocoptCompletionException(Exception):
    pass

def get_usage(cmd):
    cmd_procecss = subprocess.Popen(cmd + " --help", stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    if cmd_procecss.wait() != 0:
        raise DocoptCompletionException("Command does not exist or command help failed")
    usage = cmd_procecss.stdout.read()
    if type(usage) != str:
        # in Python 3, usage will be bytes
        usage = str(usage, "ascii")
    return usage

def get_options_descriptions(doc):
    def sanitize_line(line):
        return line.replace("'", "'\\''").replace('[', '\\[').replace(']', '\\]').strip()

    for arg in re.findall('\n  .*', doc):
        options, partition, description = arg.strip().partition('  ')
        if not partition:
            continue
        if not options.startswith('-'):
            yield options, sanitize_line(description)
            continue
        options = options.replace(',', ' ')
        options = re.sub("=\S+", "= ", options)
        for s in options.split():
            yield s, sanitize_line(description)

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

def build_command_tree(pattern, cmd_params):
    """
    Recursively fill in a command tree in CommandParams (see CommandParams documentation) according to a
    docopt-parsed "pattern" object
    """
    from docopt import Either, Optional, OneOrMore, Required, Option, Command
    if type(pattern) in [Either, Optional, OneOrMore]:
        for child in pattern.children:
            build_command_tree(child, cmd_params)
    elif type(pattern) in [Required]:
        for child in pattern.children:
            cmd_params = build_command_tree(child, cmd_params)
    elif type(pattern) in [Option]:
        suffix = "=" if pattern.argcount else ""
        if pattern.short:
            cmd_params.arguments.append(pattern.short + suffix)
        if pattern.long:
            cmd_params.arguments.append(pattern.long + suffix)
    elif type(pattern) in [Command]:
        cmd_params = cmd_params.get_subcommand(pattern.name)
    return cmd_params

def parse_params(cmd):
    # this function creates a parameter tree for the target docopt tool.
    # a parameter tree is a CommandParams instance, see the documentation of the class
    # this function also returns a second parameter, which is a dictionary of option->option help string
    from docopt import parse_doc_options, parse_pattern, formal_usage, printable_usage
    usage = get_usage(cmd)
    options = parse_doc_options(usage)
    pattern = parse_pattern(formal_usage(printable_usage(usage)), options)
    param_tree = CommandParams()
    build_command_tree(pattern, param_tree)
    return param_tree, dict(list(get_options_descriptions(usage)))

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
        f = open(file_path, "w")
        f.write(completion_file_content)
        f.close()
        print("Completion file written to {}".format(file_path))
