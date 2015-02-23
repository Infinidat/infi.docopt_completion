Overview
========
This project auto-generates shell completion files for docopt scripts.

Installation
------------
To install docopt-completion, run:

    pip install infi.docopt-completion

Alternatively, you can use easy_install.

Usage
-----
After installing the package, run:

    docopt-completion <script-name>

The utility will try to run the given script with `--help`. The given script must:

- be installed
- print a docopt-compatible usage text
- return `0` as the exit code

The utility will then generate a completion file suitable for `bash` or `zsh`
(depending on the shell installed on the system), and put the file in the correct place for the shell to use.

After running the script, tab-completion in the shell will auto-complete the available commands of the given script.


Configuration Support
--------------------
Note that not all system configurations are automatically supported. The script looks for known zsh and
bash paths, but on some systems these paths are configured differently.

In this case, you may "force" the generation of the completion file in the local directory, and place it manually in a path known to your completion system. Generation can be forced by running the command with one of the flags:

    docopt-completion <docopt-script> [--manual-zsh | --manual-bash]

For zsh, completion paths can be listed by running the command `echo $fpath`.

Also note that some old bash systems may not support tab auto-completion.
The package `bash-completion` must be installed for bash tab-completion to work.


Checking out the code
=====================

To run this code from the repository for development purposes, run the following:

    easy_install -U infi.projector
    projector devenv build
