from common import CompletionGenerator
import os

FILE_TEMPLATE = """{}\ncomplete -F _{} {}"""

SECTION_TEMPLATE = """
_{cmd_name}()
{{
    local cur prev
    _get_comp_words_by_ref cur prev
    
    if [ $COMP_CWORD -{op} {level_num} ]; then
        COMPREPLY=( $( compgen -W '{compreply}' -- $cur) ){subcommand_switch}
    fi
}}
"""

SUBCOMMAND_SWITCH_TEMPLATE = """
    else
        case ${{COMP_WORDS[{level_num}]}} in
{subcommand_cases}
        esac 
"""

CASE_TEMPLATE = """            {})
            _{}-{}
        ;;"""
 
class BashCompletion(CompletionGenerator):
    def completion_path_exists(self):
        return os.path.exists("/etc/bash_completion.d")
    
    def get_completion_filepath(self, cmd):
        return "/etc/bash_completion.d/{}.sh".format(cmd)
    
    def create_subcommand_switch(self, cmd_name, level_num, subcommands, args):
        if len(subcommands) == 0:
            return ""
        subcommand_cases = '\n'.join(CASE_TEMPLATE.format(subcommand,
                                                           cmd_name,
                                                           subcommand) for subcommand in subcommands)
        return SUBCOMMAND_SWITCH_TEMPLATE.format(level_num=level_num, subcommand_cases=subcommand_cases)
    
    def create_compreply(self, subcommands, args):
        return " ".join(args) + " ".join(subcommands.keys())
    
    def create_section(self, cmd_name, param_tree, option_help, level_num):
        subcommands = param_tree.subcommands
        args = param_tree.arguments
        subcommand_switch = self.create_subcommand_switch(cmd_name, level_num, subcommands, args)
        res = SECTION_TEMPLATE.format(cmd_name=cmd_name,
                                      level_num=level_num,
                                      compreply = self.create_compreply(subcommands, args),
                                      subcommand_switch=subcommand_switch,
                                      op="eq" if len(subcommands) > 0 else 'ge')
        for subcommand_name, subcommand_tree in subcommands.items():
            res += self.create_section("{}-{}".format(cmd_name, subcommand_name),
                                       subcommand_tree,
                                       option_help,
                                       level_num+1)
        return res
    
    def get_completion_file_content(self, cmd, param_tree, option_help):
        completion_file_inner_content = self.create_section(cmd, param_tree, option_help, 1)
        return FILE_TEMPLATE.format(completion_file_inner_content, cmd, cmd)
