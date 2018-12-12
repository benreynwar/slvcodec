from slvcodec import math_parser, filetestbench_generator, vhdl_parser


logceil = math_parser.logceil
logceil_1to0 = math_parser.logceil_1to0
add_slvcodec_files = filetestbench_generator.add_slvcodec_files
make_add_slvcodec_files_and_setgenerics_wrapper = \
    filetestbench_generator.make_add_slvcodec_files_and_setgenerics_wrapper
parse_and_resolve_files = vhdl_parser.parse_and_resolve_files
