import os
import glob
from .common import CompletionGenerator

# We fill the file template with the command name and the different sections
# generated from the templates below.
# _message_next_arg: outputs the next positional argument name to the user
# with the _message function. It counts the number of elements in the 'words'
# special array that don't begin with '-' (options) and then uses the myargs
# array defined by the caller to output the correct argument name.
# We skip the first two elements in 'words' because the first is always empty and
# the second is the last keyword before the options and arguments start.
FILE_TEMPLATE = '''#compdef {0}

_message_next_arg()
{{
    argcount=0
    for word in "${{words[@][2,-1]}}"
    do
        if [[ $word != -* ]] ; then
            ((argcount++))
        fi
    done
    if [[ $argcount -le ${{#myargs[@]}} ]] ; then
        _message -r $myargs[$argcount]
        if [[ $myargs[$argcount] =~ ".*file.*" || $myargs[$argcount] =~ ".*path.*" ]] ; then
            _files
        fi
    fi
}}
{1}

_{0} "$@"'''

# this is a template of a function called by the completion system when crawling the arguments already
# typed. there is a section for every command and sub-command that the target script supports.
# the variables in the function, "state" and "line" are filled by the _arguments call.
# these variables are handled in "subcommand_switch", which is filled using the SUBCOMMAND_SWITCH_TEMPLATE template
SECTION_TEMPLATE = """
_{cmd_name} ()
{{
    local context state state_descr line
    typeset -A opt_args

    _arguments -C \\
        ':command:->command' \\{opt_list}
        {subcommand_switch}
}}
"""

# if "state" is "command", we call _values which lists the next available options. if state is "options" it means
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
            _values '{subcommand}' $subcommands
        ;;

        (options)
            case $line[1] in
{subcommand_cases}
            esac
        ;;
    esac
"""

CASE_TEMPLATE = """                {0})
                    _{1}-{0}
                ;;"""

# When there are positional arguments to the handled context, we use this tempalte.
# We output the name of the next positional argument by using the _message_next_args
# function (defined in FILE_TEMPLATE), unless the current word starts with "-" which means
# the user is trying to type an option (then we specify the available options by using
# _arguments, as in the regular SECTION_TEMPLATE)
ARG_SECTION_TEMPLATE = """
_{cmd_name} ()
{{
    local context state state_descr line
    typeset -A opt_args

    if [[ $words[$CURRENT] == -* ]] ; then
        _arguments -C \\
        ':command:->command' \\{opt_list}

    else
        myargs=({args})
        _message_next_arg
    fi
}}
"""

class ZshCompletion(CompletionGenerator):
    """ Base class for generating ZSH completion files"""

    # The completion paths defined here (the base class) are used if manual file generation is specified.
    # the paths are redefined in subclasses for automatic generation

    def get_completion_path(self):
        return "."

    def get_completion_filepath(self, cmd):
        return os.path.join(self.get_completion_path(), "_{0}".format(cmd))

    def create_opt_menu(self, opts, option_help):
        if not opts:
            return ""
        # this menu is added to the _arguments call and describes the options
        show_help = all(opt in option_help for opt in opts)  # show help only if all options have help
        def get_option_help(opt):
            if not show_help or opt not in option_help:
                return ''
            return "[{0}]".format(option_help[opt])
        def decorate_opt(opt):
            # add "-" to opts that end with "="
            # '=-' to _arguments means that "=" is appended to the option upon completion
            return (opt + "-") if opt.endswith("=") else opt
        return '\n' + '\n'.join(["\t\t'({0}){0}{1}' \\".format(decorate_opt(opt), get_option_help(opt))
                                 for opt in opts])

    def create_subcommand_cases(self, cmd_name, subcmds):
        # the subcommand menu is added to the switch-case of line[1], which tests the next subcommand.
        # the switch-case directs the next sub-command to its relevant section (function)
        return '\n'.join([CASE_TEMPLATE.format(cmd, cmd_name) for cmd in subcmds])

    def create_subcommand_list(self, cmd_name, option_help, subcmds):
        def get_subcmd_help(subcmd):
            # help for subcommands contains the trail, with or without the script name. extract that from cmd_name
            for i in [0, 1]:
                subcommand_with_trail = ' '.join(cmd_name.replace("-", " ").split()[i:] + [subcmd])
                if subcommand_with_trail in option_help:
                    return option_help[subcommand_with_trail]
            return None
        # show help only if all subcommands have help
        show_help = all(get_subcmd_help(subcmd) is not None for subcmd in subcmds)
        def get_help_opt(subcmd):
            if not show_help:
                return ''
            return "[{0}]".format(get_subcmd_help(subcmd))
        # the subcommand list is filled into the "subcommands" variable which is sent to the _values command,
        # to specify the next completion options. It includes all the next available sub-commands
        return '\n'.join(["\t\t\t\t'{0}{1}'".format(subcmd, get_help_opt(subcmd)) for subcmd in subcmds])

    def create_subcommand_switch(self, cmd_name, option_help, subcommands):
        if len(subcommands) == 0:
            return ""
        subcommand_list = self.create_subcommand_list(cmd_name, option_help, subcommands.keys())
        subcommand_cases = self.create_subcommand_cases(cmd_name, subcommands.keys())
        return SUBCOMMAND_SWITCH_TEMPLATE.format(subcommand_list=subcommand_list,
                                                 subcommand_cases=subcommand_cases,
                                                 subcommand=cmd_name.replace('-', ' '))

    def create_args_section(self, cmd_name, opt_list, args):
        res = ARG_SECTION_TEMPLATE.format(cmd_name="{}".format(cmd_name),
                                           args=' '.join("'{}'".format(arg) for arg in args),
                                           opt_list=opt_list)
        return res

    def create_section(self, cmd_name, param_tree, option_help):
        subcommands = param_tree.subcommands
        opts = param_tree.options
        args = param_tree.arguments
        opt_list = self.create_opt_menu(opts, option_help)
        if args:
            # when we have an argument we move the completion system to arguments-or-options only section,
            # this means we DON'T support a script that has a arguments-or-subcommands part like:
            # script-name.py (<some-arg> | (a-subcommand <command-arg>))
            return self.create_args_section(cmd_name, opt_list, args)
        subcommand_switch = self.create_subcommand_switch(cmd_name, option_help, subcommands)
        res = SECTION_TEMPLATE.format(cmd_name=cmd_name,
                                      opt_list=opt_list,
                                      subcommand_switch=subcommand_switch)
        for subcommand_name, subcommand_tree in subcommands.items():
            res += self.create_section("{0}-{1}".format(cmd_name, subcommand_name), subcommand_tree, option_help)
        return res

    def get_completion_file_content(self, cmd, param_tree, option_help):
        completion_file_inner_content = self.create_section(cmd, param_tree, option_help)
        return FILE_TEMPLATE.format(cmd, completion_file_inner_content)

class OhMyZshCompletion(ZshCompletion):
    def get_name(self):
        return "ZSH with oh-my-zsh"

    def get_completion_path(self):
        return os.path.expanduser('~/.oh-my-zsh')

    def get_completion_filepath(self, cmd):
        completion_path = os.path.expanduser('~/.oh-my-zsh/completions')
        if not os.path.exists(completion_path):
            os.makedirs(completion_path)
        return os.path.join(completion_path, "_{0}".format(cmd))

class ZshPreztoCompletion(ZshCompletion):
    def get_name(self):
        return "ZSH with Prezto"

    def get_completion_path(self):
        return os.path.expanduser('~/.zprezto')

    def get_completion_filepath(self, cmd):
        completion_path = os.path.expanduser("~/.zprezto/modules/completion/external/src")
        return os.path.join(completion_path, "_{0}".format(cmd))

class ZshUsrShareCompletion(ZshCompletion):
    def get_name(self):
        return "ZSH with no addons"

    def get_completion_path(self):
        return "/usr/share/zsh/*/functions"

    def _get_completion_paths(self):
        # Examples of paths we support:
        # - /usr/share/zsh/5.0.1/functions/Completion
        # - /usr/share/zsh/5.0.1/functions
        # - /usr/share/zsh/functions/Completion
        # - /usr/share/zsh/functions
        paths_to_check = [self.get_completion_path(), self.get_completion_path().replace("/*", "")]
        for path_to_check in paths_to_check:
            for path in glob.glob(path_to_check):
                path_with_completion = os.path.join(path, "Completion")
                if os.path.exists(path_with_completion):
                    path = path_with_completion
                yield path

    def completion_path_exists(self):
        return any(os.path.exists(path) for path in self._get_completion_paths())

    def get_completion_filepath(self, cmd):
        for completion_path in self._get_completion_paths():
            yield os.path.join(completion_path, "_{0}".format(cmd))
