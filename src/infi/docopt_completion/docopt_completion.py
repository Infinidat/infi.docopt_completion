from __future__ import print_function
import sys
import os
import docopt
from .bash import BashCompletion
from .zsh import OhMyZshCompletion, ZshPreztoCompletion, ZshUsrShareCompletion, ZshCompletion
from .common import DocoptCompletionException, parse_params

USAGE = """Usage:
    docopt-completion <docopt-script> [--manual-zsh | --manual-bash]
    docopt-completion --help

Options:
    --manual-zsh        Do not attempt to find completion paths automatically. Output ZSH completion file to local directory
    --manual-bash       Do not attempt to find completion paths automatically. Output BASH completion file to local directory    
"""

def _autodetect_generators():
    completion_generators = [OhMyZshCompletion(),
                             ZshPreztoCompletion(),
                             ZshUsrShareCompletion(),
                             BashCompletion()]
    generators_to_use = [generator for generator in completion_generators if generator.completion_path_exists()]
    
    if len(generators_to_use) == 0:
        raise DocoptCompletionException("No completion paths found.")

    return generators_to_use

def docopt_completion(cmd, manual_zsh=False, manual_bash=False):
    if os.sep in cmd:
        raise DocoptCompletionException("Command cannot contain '{}'".format(os.sep))
    
    if manual_zsh:
        generators_to_use = [ZshCompletion()]
    elif manual_bash:
        generators_to_use = [BashCompletion()]
    else:
        generators_to_use = _autodetect_generators()
    
    param_tree, option_help = parse_params(cmd)
        
    for generator in generators_to_use:
        generator.generate(cmd, param_tree, option_help)

def main():
    arguments = docopt.docopt(USAGE)
    cmd = arguments["<docopt-script>"]
    manual_bash = arguments["--manual-bash"]
    manual_zsh = arguments["--manual-zsh"]
    try:
        docopt_completion(cmd, manual_zsh, manual_bash)
    except DocoptCompletionException as e:
        print(e.args[0])
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())
