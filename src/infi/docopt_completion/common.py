from __future__ import print_function
import subprocess
import re
import os
import types

class DocoptCompletionException(Exception):
    pass

def get_usage(cmd):
    cmd_process = subprocess.Popen(cmd + " --help", stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    # Poll process for new output until finished
    usage = bytes()
    while True:
        nextline = cmd_process.stdout.readline()
        if len(nextline) == 0 and cmd_process.poll() is not None:
            break
        usage += nextline
    if cmd_process.returncode != 0:
        raise DocoptCompletionException("Command does not exist or command help failed")
    return usage.decode("ascii")

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
    """ contains command options, arguments and subcommands.
    options are optional arguments like "-v", "-h", etc.
    arguments are required arguments like file paths, etc.
    subcommands are optional keywords, like the "status" in "git status".
    subcommands have their own CommandParams instance, so the "status" in "git status" can
    have its own options, arguments and subcommands.
    This way we can describe commands like "git remote add origin --fetch" with all the different
    options at each level """
    def __init__(self):
        self.arguments = []
        self.options = []
        self.subcommands = {}

    def get_subcommand(self, subcommand):
        return self.subcommands.setdefault(subcommand, CommandParams())

def build_command_tree(pattern, cmd_params):
    """
    Recursively fill in a command tree in CommandParams (see CommandParams documentation) according to a
    docopt-parsed "pattern" object
    """
    from docopt import Either, Optional, OneOrMore, Required, Option, Command, Argument
    if type(pattern) in [Either, Optional, OneOrMore]:
        for child in pattern.children:
            build_command_tree(child, cmd_params)
    elif type(pattern) in [Required]:
        for child in pattern.children:
            cmd_params = build_command_tree(child, cmd_params)
    elif type(pattern) in [Option]:
        suffix = "=" if pattern.argcount else ""
        if pattern.short:
            cmd_params.options.append(pattern.short + suffix)
        if pattern.long:
            cmd_params.options.append(pattern.long + suffix)
    elif type(pattern) in [Command]:
        cmd_params = cmd_params.get_subcommand(pattern.name)
    elif type(pattern) in [Argument]:
        cmd_params.arguments.append(pattern.name)
    return cmd_params

def parse_params(cmd):
    # this function creates a parameter tree for the target docopt tool.
    # a parameter tree is a CommandParams instance, see the documentation of the class
    # this function also returns a second parameter, which is a dictionary of option->option help string
    from docopt import parse_defaults, parse_pattern, formal_usage, printable_usage
    usage = get_usage(cmd)
    options = parse_defaults(usage)
    pattern = parse_pattern(formal_usage(printable_usage(usage)), options)
    param_tree = CommandParams()
    build_command_tree(pattern, param_tree)
    return param_tree, dict(list(get_options_descriptions(usage)))

class CompletionGenerator(object):
    """ base class for completion file generators """
    def get_name(self):
        raise NotImplementedError()
    
    def get_completion_path(self):
        raise NotImplementedError()

    def get_completion_filepath(self, cmd):
        raise NotImplementedError()

    def get_completion_file_content(self, cmd, param_tree, option_help):
        raise NotImplementedError()

    def completion_path_exists(self):
        return os.path.exists(self.get_completion_path())

    def _write_to_file(self, file_path, completion_file_content):
        if not os.access(os.path.dirname(file_path), os.W_OK):
            print("Skipping file {}, no permissions".format(file_path))
            return
        try:
            with open(file_path, "w") as fd:
                fd.write(completion_file_content)
        except IOError:
            print("Failed to write {}".format(file_path))
            return
        print("Completion file written to {}".format(file_path))

    def generate(self, cmd, param_tree, option_help):
        completion_file_content = self.get_completion_file_content(cmd, param_tree, option_help)
        file_paths = self.get_completion_filepath(cmd)
        if not isinstance(file_paths, types.GeneratorType):
            file_paths = [file_paths]
        for file_path in file_paths:
            self._write_to_file(file_path, completion_file_content)
