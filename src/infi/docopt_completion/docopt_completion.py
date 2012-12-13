import sys
from bash import BashCompletion
from zsh import OhMyZshCompletion, ZshPreztoCompletion
from common import DocoptCompletionException, parse_params

def docopt_completion(cmd):
    completion_generators = [OhMyZshCompletion(),
                             ZshPreztoCompletion(),
                             BashCompletion()]
    generators_to_use = [generator for generator in completion_generators if generator.completion_path_exists()]
    
    if len(generators_to_use) == 0:
        print "No completion paths found."
        return 1
    
    try:
        param_tree, option_help = parse_params(cmd)
    except DocoptCompletionException, e:
        print e.message
        return 1
        
    for generator in generators_to_use:
        generator.generate(cmd, param_tree, option_help)
    
    return 0

def main():
    if len(sys.argv) != 2:
        print "Usage: {} <docopt-script>".format(sys.argv[0])
        return 1
    program, cmd = sys.argv
    return docopt_completion(cmd)

if __name__ == "__main__":
    sys.exit(main())
