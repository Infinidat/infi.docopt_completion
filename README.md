Overview
========
This project auto-generates shell completion files for docopt scripts.

Usage
-----
After installing the package, run:

    docopt-completion <script-name>
    
The utility will try to run the given script with --help. The given script must be installed, and print a
docopt-compatible usage text and return 0 as the exit code.
The utility will then generate a completion file suitable for bash or zsh (depending on the shell installed on the
system) and place that file in the correct place for the shell to use.
After running the script, tab-completion in the shell will auto-complete the available commands of the given script.

Note: some old bash systems may not support tab auto-completion. The package 'bash-completion' must be installed on
the operating system.

Checking out the code
=====================

This project uses buildout and infi-projector, and git to generate setup.py and __version__.py.
In order to generate these, first get infi-projector:

    easy_install infi.projector

and then run in the project directory:

    projector devenv build

To use the plugin directly from the source, run:

    python setup.py develop
