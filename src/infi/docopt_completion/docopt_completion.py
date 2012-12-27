from __future__ import print_function
import sys
from .bash import BashCompletion
from .zsh import OhMyZshCompletion, ZshPreztoCompletion
from .common import DocoptCompletionException, parse_params

def docopt_completion(cmd):
    completion_generators = [OhMyZshCompletion(),
                             ZshPreztoCompletion(),
                             BashCompletion()]
    generators_to_use = [generator for generator in completion_generators if generator.completion_path_exists()]
    
    if len(generators_to_use) == 0:
        raise DocoptCompletionException("No completion paths found.")
    
    param_tree, option_help = parse_params(cmd)
        
    for generator in generators_to_use:
        generator.generate(cmd, param_tree, option_help)

def main():
    if len(sys.argv) != 2:
        print("Usage: {} <docopt-script>".format(sys.argv[0]))
        return 1
    program, cmd = sys.argv
    try:
        docopt_completion(cmd)
    except DocoptCompletionException as e:
        print(e.args[0])
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())
