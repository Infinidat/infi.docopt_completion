import os
from common import CompletionGenerator

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
{subcommand_cases}
			esac
		;;
	esac
"""

CASE_TEMPLATE = """				{})
					_{}-{}
				;;"""

class ZshCompletion(CompletionGenerator):
    def completion_path_exists(self):
        raise NotImplementedError()       # implemented in subclasses
    
    def get_completion_filepath(self, cmd):
        raise NotImplementedError()       # implemented in subclasses
    
    def create_arg_menu(self, args, option_help):
        # this menu is added to the _arguments call and describes the optional arguments
        show_help = all(arg in option_help for arg in args) # show help only if all options have help
        def get_help_opt(arg):
            if not show_help or arg not in option_help:
                return ''
            return "[{}]".format(option_help[arg])
        def decorate_arg(arg):
            # add "-" to args that end with "="
            # '=-' to _arguments means that "=" is appended to the option upon completion            
            return (arg + "-") if arg.endswith("=") else arg
        return '\n'.join(["\t\t'({0}){0}{1}' \\".format(decorate_arg(arg), get_help_opt(arg)) for arg in args])
    
    def create_subcommand_cases(self, cmd_name, subcmds):
        # the subcommand menu is added to the switch-case of line[1], which tests the next subcommand.
        # the switch-case directs the next sub-command to its relevant section (function)
        return '\n'.join([CASE_TEMPLATE.format(cmd, cmd_name, cmd) for cmd in subcmds])
    
    def create_subcommand_list(self, subcmds):
        # the subcommand list is filled into the "subcommands" variable which is sent to the _describe command,
        # to specify the next completion options. It includes all the next available sub-commands
        return '\n'.join(["\t\t\t\t'{}'".format(subcmd) for subcmd in subcmds])
    
    def create_subcommand_switch(self, cmd_name, subcommands):
        if len(subcommands) == 0:
            return ""
        subcommand_list = self.create_subcommand_list(subcommands.keys())
        subcommand_cases = self.create_subcommand_cases(cmd_name, subcommands.keys())
        return SUBCOMMAND_SWITCH_TEMPLATE.format(subcommand_list=subcommand_list,
                                                 subcommand_cases=subcommand_cases,
                                                 subcommand=cmd_name.replace('-', ' '))
    
    def create_section(self, cmd_name, param_tree, option_help):
        subcommands = param_tree.subcommands
        args = param_tree.arguments
        if args:
            arg_list = '\n' + self.create_arg_menu(args, option_help)
        else:
            arg_list = ""
        subcommand_switch = self.create_subcommand_switch(cmd_name, subcommands)
        res = SECTION_TEMPLATE.format(cmd_name=cmd_name,
                                      arg_list=arg_list,
                                      subcommand_switch=subcommand_switch)
        for subcommand_name, subcommand_tree in subcommands.items():
            res += self.create_section("{}-{}".format(cmd_name, subcommand_name), subcommand_tree, option_help)
        return res

    def get_completion_file_content(self, cmd, param_tree, option_help):
        completion_file_inner_content = self.create_section(cmd, param_tree, option_help)
        return FILE_TEMPLATE.format(cmd, completion_file_inner_content, cmd)
    
class OhMyZshCompletion(ZshCompletion):
    def completion_path_exists(self):
        return os.path.exists(os.path.expanduser('~/.oh-my-zsh'))
    
    def get_completion_filepath(self, cmd):
        # completion paths are paths under the $fpath variable of zsh. However since we can't get $fpath, we
        # try to use the default path
        completion_path = os.path.expanduser('~/.oh-my-zsh/completions')
        if not os.path.exists(completion_path):
            os.makedirs(completion_path)
        return os.path.join(completion_path, "_{}".format(cmd))

class ZshPreztoCompletion(ZshCompletion):
    def completion_path_exists(self):
        return os.path.exists(os.path.expanduser('~/.zprezto'))
    
    def get_completion_filepath(self, cmd):
        completion_path  = os.path.expanduser("~/.zprezto/modules/completion/external/src")
        return os.path.join(completion_path, "_{}".format(cmd))
    