import os
import re
import sys
import subprocess

class DocopyCompletionException(Exception):
    pass

FILE_TEMPLATE = '#compdef {}\n\n{}\n\n_{} "$@"'

# this is a template of a function called by the completion system when crawling the arguments already
# typed. there is a section for every command and sub-command that the target script supports.
# the variables in the function, "state" and "line" are filled by the _arguments call.
# these variables are handled in "subcommand_switch", which is filled using the SUBCOMMAND_SWITCH_TEMPLATE template
SECTION_TEMPLATE = """
_{cmd_name} ()
{{
	local curcontext="$curcontext" state line
	typeset -A opt_args

	_arguments -C \\
		':command:->command' \\{arg_list}
		{subcommand_switch}
}}
"""

# if "state" is "command", we call _describe which lists the next available options. if state is "options" it means
# that there are more commands typed after the currently handled command, and in that case we use line[1] (the next
# option) to direct the completion system to the next section
# note that the options context is added to the _arguments call here, because this context is only supported when
# there are subcommands
SUBCOMMAND_SWITCH_TEMPLATE = """'*::options:->options'

	case $state in
		(command)
			local -a subcommands
			subcommands=(
{subcommand_list}
			)
			_describe -t commands '{subcommand}' subcommands
		;;

		(options)
			case $line[1] in
{subcommand_menu}
			esac
		;;
	esac
"""

def strip_usage_line(line):
    # we don't support option arguments or group selectors yet
    # just strip everything that is irrelevant
    line = line.strip()
    for strip_char in "()[]|":
        line = line.replace(strip_char, '')
    line = re.sub('<.*?>', '', line)
    line = re.sub('=.*?( |$)', ' ', line)
    return line

def get_usage(cmd):
    cmd_procecss = subprocess.Popen(cmd + " --help", stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    if cmd_procecss.wait() != 0:
        raise DocopyCompletionException("Command does not exist or command help failed")
    usage_lines = cmd_procecss.stdout.read()
    usage_lines = usage_lines
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
        line = re.sub('=.*?( |$)', ' ', line)
        return line.replace("'", "'\\''").replace('[', '\\[').replace(']', '\\]').strip().split(None, 1)
    return dict(sanitize_line(line) for line in options_lines)

def parse_params(cmd):
    # this function creates an argument tree for the target docopt tool.
    # an argument tree is an "argument dictionary", which contains two items:
    #  "argumnets": list of optional arguments
    #  "subcommands": dictionary of command-name -> another "argument dictionary" of the command
    # this function also returns a second parameter, which is a dictionary of option->option help string
    usage = get_usage(cmd)
    usage_lines, options_lines = split_usage_lines(usage)
    param_tree = {}
    for line in usage_lines:
        line = strip_usage_line(line)
        args = line.split()[1:]
        current_tree = param_tree
        while len(args) > 0:
            arg = args.pop(0)
            if arg.startswith('-'):
                current_tree.setdefault("arguments", []).append(arg)
            else:
                current_tree.setdefault("subcommands", {}).setdefault(arg, {})
                current_tree = current_tree["subcommands"][arg]
    return param_tree, parse_option_lines(options_lines)

def create_arg_menu(args, option_help):
    # this menu is added to the _arguments call and describes the optional arguments
    show_help = all(arg in option_help for arg in args) # show help only if all options have help
    def get_help_opt(arg):
        if not show_help or arg not in option_help:
            return ''
        return "[{}]".format(option_help[arg])
    return '\n'.join(["\t\t'({}){}{}' \\".format(arg, arg, get_help_opt(arg)) for arg in args])

def create_subcommand_menu(cmd_name, subcmds):
    # the subcommand menu is added to the switch-case of line[1], which tests the next subcommand.
    # the switch-case directs the next sub-command to its relevant section (function)
    return '\n'.join(["""\t\t\t\t({})\n\t\t\t\t\t_{}-{}\n\t\t\t\t;;""".format(cmd, cmd_name, cmd) for cmd in subcmds])

def create_subcommand_list(subcmds):
    # the subcommand list is filled into the "subcommands" variable which is sent to the _describe command, to specify
    # the next completion options. It includes all the next available sub-commands
    return '\n'.join(["\t\t\t\t'{}'".format(subcmd) for subcmd in subcmds])

def create_section(cmd_name, param_tree, option_help):
    subcommands = param_tree.get("subcommands", {})
    args = param_tree.get("arguments", [])
    if args:
        arg_list = '\n' + create_arg_menu(args, option_help)
    else:
        arg_list = ""
    if subcommands:
        subcommand_list = create_subcommand_list(subcommands.keys())
        subcommand_menu = create_subcommand_menu(cmd_name, subcommands.keys())
        subcommand_switch = SUBCOMMAND_SWITCH_TEMPLATE.format(subcommand_list=subcommand_list,
                                                                     subcommand_menu=subcommand_menu,
                                                                     subcommand=cmd_name.replace('-', ' '))
    else:
        subcommand_switch = ""
    res = SECTION_TEMPLATE.format(cmd_name=cmd_name,
                                  arg_list=arg_list,
                                  subcommand_switch=subcommand_switch)
    for subcommand_name, subcommand_tree in subcommands.items():
        res += create_section("{}-{}".format(cmd_name, subcommand_name), subcommand_tree, option_help)
    return res

def get_completion_filepath(cmd):
    # completion paths are paths under the $fpath variable of zsh. However since we can't get $fpath, we
    # try to use the default paths for prezto and oh-my-zsh
    if os.path.exists(os.path.expanduser('~/.zprezto')):
        completion_path  = os.path.expanduser("~/.zprezto/modules/completion/external/src")
    elif os.path.exists(os.path.expanduser('~/.oh-my-zsh')):
        completion_path = os.path.expanduser('~/.oh-my-zsh/completions')
    else:
        raise DocopyCompletionException("Could not find path for completion file")
    if not os.path.exists(completion_path):
        os.makedirs(completion_path)
    return os.path.join(completion_path, "_{}".format(cmd))

def create_completion_file(cmd):
    param_tree, option_help = parse_params(cmd)
    completion_file_content = create_section(cmd, param_tree, option_help)
    completion_file_content = FILE_TEMPLATE.format(cmd, completion_file_content, cmd)
    file_path = get_completion_filepath(cmd)
    open(file_path, "wb").write(completion_file_content)
    print "Completion file written to {}".format(file_path)

def main():
    if len(sys.argv) != 2:
        print "Usage: {} <docopt-script>".format(sys.argv[0])
        return 1
    program, cmd = sys.argv
    try:
        create_completion_file(cmd)
    except DocopyCompletionException, e:
        print e.message
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())
    