import sys
import time

# from pandaserver.taskbuffer.TaskBuffer import taskBuffer
# from pandaserver.configurator import db_interface as dbif
from pandacommon.pandalogger import logger_utils
from pandaserver.configurator import Configurator as configurator_module
from pandaserver.configurator.Configurator import Configurator, NetworkConfigurator, JsonDumper


# logger
base_logger = configurator_module._logger


# main
def main(argv=tuple(), tbuf=None, **kwargs):
    # If no argument, call the basic configurator
    if len(argv) == 1:
        _logger = logger_utils.make_logger(base_logger, 'Configurator')
        t1 = time.time()
        configurator = Configurator()
        if not configurator.run():
            _logger.critical('Configurator loop FAILED')
        t2 = time.time()
        _logger.debug('Configurator run took {0}s'.format(t2-t1))

    # If --network argument, call the network configurator
    elif len(argv) == 2 and argv[1].lower() == '--network':
        _logger = logger_utils.make_logger(base_logger, 'NetworkConfigurator')
        t1 = time.time()
        network_configurator = NetworkConfigurator()
        if not network_configurator.run():
            _logger.critical('Configurator loop FAILED')
        t2 = time.time()
        _logger.debug(' run took {0}s'.format(t2-t1))

    # If --json_dump
    elif len(argv) == 2 and argv[1].lower() == '--json_dump':
        _logger = logger_utils.make_logger(base_logger, 'JsonDumper')
        t1 = time.time()
        json_dumper = JsonDumper()
        out_msg = json_dumper.run()
        _logger.debug('Json_dumper finished with {0}'.format(out_msg))
        t2 = time.time()
        _logger.debug(' run took {0}s'.format(t2-t1))
    else:
        _logger.error('Configurator being called with wrong arguments. Use either no arguments or --network or --json_dump')


# run
if __name__ == '__main__':
    main(argv=sys.argv)
