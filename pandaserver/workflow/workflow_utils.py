import copy
import six
import re
import shlex
import json

from pandaclient import PrunScript


# extract argument value from execution string
def get_arg_value(arg, exec_str):
    args = shlex.split(exec_str)
    if arg in args:
        return args[args.index(arg)+1]
    for item in args:
        if item.startswith(arg):
            return item.split('=')[-1]
    return None


# DAG vertex
class Node (object):

    def __init__(self, id, node_type, data, is_leaf, name):
        self.id = id
        self.type = node_type
        self.data = data
        self.is_leaf = is_leaf
        self.is_tail = False
        self.inputs = {}
        self.outputs = {}
        self.output_types = []
        self.scatter = None
        self.parents = set()
        self.name = name
        self.sub_nodes = set()
        self.root_inputs = None
        self.task_params = None
        self.condition = None

    def add_parent(self, id):
        self.parents.add(id)

    def set_input_value(self, key, src_key, src_value):
        if isinstance(self.inputs[key]['source'], list):
            self.inputs[key].setdefault('value', copy.copy(self.inputs[key]['source']))
            tmp_list = []
            for k in self.inputs[key]['value']:
                if k == src_key:
                    tmp_list.append(src_value)
                else:
                    tmp_list.append(k)
            self.inputs[key]['value'] = tmp_list
        else:
            self.inputs[key]['value'] = src_value

    # convert inputs to dict inputs
    def convert_dict_inputs(self):
        data = {}
        for k, v in six.iteritems(self.inputs):
            y_name = k.split('/')[-1]
            if 'value' in v:
                data[y_name] = v['value']
            elif 'default' in v:
                data[y_name] = v['default']
            else:
                raise ReferenceError("{} is not resolved".format(k))
        return data

    # convert outputs to set
    def convert_set_outputs(self):
        data = set()
        for k, v in six.iteritems(self.outputs):
            if 'value' in v:
                data.add(v['value'])
        return data

    # string representation
    def __str__(self):
        outstr = "ID:{} Name:{} Type:{}\n".format(self.id, self.name, self.type)
        outstr += "  Parent:{}\n".format(','.join([str(p) for p in self.parents]))
        outstr += "  Input:\n"
        for k, v in six.iteritems(self.convert_dict_inputs()):
            outstr += "     {}: {}\n".format(k, v)
        outstr += "  Output:\n"
        for k, v in six.iteritems(self.outputs):
            if 'value' in v:
                v = v['value']
            else:
                v = 'NA'
            outstr += "     {}\n".format(v)
        return outstr

    # resolve workload-specific parameters
    def resolve_params(self, task_template=None, id_map=None):
        if self.type == 'prun':
            dict_inputs = self.convert_dict_inputs()
            if 'opt_secondaryDSs' in dict_inputs:
                idx = 1
                for ds_name, ds_type in zip(dict_inputs['opt_secondaryDSs'], dict_inputs['opt_secondaryDsTypes']):
                    src = "%%DS{}%%".format(idx)
                    dst = "{}.{}".format(ds_name, ds_type)
                    dict_inputs['opt_exec'] = re.sub(src, dst, dict_inputs['opt_exec'])
                    dict_inputs['opt_args'] = re.sub(src, dst, dict_inputs['opt_args'])
                    idx += 1
                for k, v in six.iteritems(self.inputs):
                    if k.endswith('opt_exec'):
                        v['value'] = dict_inputs['opt_exec']
                    elif k.endswith('opt_args'):
                        v['value'] = dict_inputs['opt_args']
        if task_template:
            self.task_params = self.make_task_params(task_template, id_map)
        [n.resolve_params(task_template, id_map) for n in self.sub_nodes]

    # create task params
    def make_task_params(self, task_template, id_map):
        if self.type == 'prun':
            dict_inputs = self.convert_dict_inputs()
            # check type
            use_athena = False
            if 'opt_useAthenaPackages' in dict_inputs and dict_inputs['opt_useAthenaPackages']:
                use_athena = True
            container_image = None
            if 'opt_containerImage' in dict_inputs and dict_inputs['opt_containerImage']:
                container_image = dict_inputs['opt_containerImage']
            if use_athena:
                task_params = copy.deepcopy(task_template['athena'])
            else:
                task_params = copy.deepcopy(task_template['container'])
            # task name
            for k, v in six.iteritems(self.outputs):
                task_name = v['value']
                break
            task_params['taskName'] = task_name
            # architecture
            if 'opt_architecture' in dict_inputs and dict_inputs['opt_architecture']:
                task_params['architecture'] = dict_inputs['opt_architecture']
            # cli params
            com = ['prun', '--exec', dict_inputs['opt_exec'], *shlex.split(dict_inputs['opt_args'])]
            in_ds_str = None
            if 'opt_inDS' in dict_inputs and dict_inputs['opt_inDS']:
                if isinstance(dict_inputs['opt_inDS'], list):
                    is_list_in_ds = True
                else:
                    is_list_in_ds = False
                if 'opt_inDsType' not in dict_inputs or not dict_inputs['opt_inDsType']:
                    if is_list_in_ds:
                        in_ds_suffix = []
                        in_ds_list = dict_inputs['opt_inDS']
                    else:
                        in_ds_suffix = None
                        in_ds_list = [dict_inputs['opt_inDS']]
                    for tmp_in_ds in in_ds_list:
                        for parent_id in self.parents:
                            parent_node = id_map[parent_id]
                            if tmp_in_ds in parent_node.convert_set_outputs():
                                if is_list_in_ds:
                                    in_ds_suffix.append(parent_node.output_types[0])
                                else:
                                    in_ds_suffix = parent_node.output_types[0]
                                break
                else:
                    in_ds_suffix = dict_inputs['opt_inDsType']
                if is_list_in_ds:
                    in_ds_str = ','.join(['{}_{}/'.format(s1, s2) for s1, s2 in zip(dict_inputs['opt_inDS'],
                                                                                   in_ds_suffix)])
                else:
                    in_ds_str = '{}_{}/'.format(dict_inputs['opt_inDS'], in_ds_suffix)
                com += ['--inDS', in_ds_str]
            com += ['--outDS', task_name]
            if container_image:
                com += ['--containerImage', container_image]
            # parse args before setting --useAthenaPackages since it requires real Athena runtime
            parsed_params = PrunScript.main(True, com[1:], dry_mode=True)
            if use_athena:
                com += ['--useAthenaPackages']
            task_params['cliParams'] = ' '.join(shlex.quote(x) for x in com)
            # set parsed parameters
            for p_key, p_value in six.iteritems(parsed_params):
                if p_key not in task_params or p_key in ['jobParameters']:
                    task_params[p_key] = p_value
            if 'buildSpec' not in parsed_params and 'buildSpec' in task_params:
                del task_params['buildSpec']
            # outputs
            for tmp_item in task_params['jobParameters']:
                if tmp_item['type'] == 'template' and tmp_item["param_type"] == "output":
                    self.output_types.append(re.search(r'}\.(.+)$', tmp_item["value"]).group(1))
            # container
            if not container_image:
                if 'container_name' in task_params:
                    del task_params['container_name']
                if 'multiStepExec' in task_params:
                    del task_params['multiStepExec']
            # parent
            if self.parents and len(self.parents) == 1:
                task_params['noWaitParent'] = True
                task_params['parentTaskName'] = id_map[list(self.parents)[0]].task_params['taskName']
            # return
            return task_params
        return None


# dump nodes
def dump_nodes(node_list, dump_str=None, only_leaves=True):
    if dump_str is None:
        dump_str = '\n'
    for node in node_list:
        if node.is_leaf:
            dump_str += "{}".format(node)
            if node.task_params:
                dump_str += json.dumps(node.task_params, indent=4, sort_keys=True)
                dump_str += '\n\n'
        else:
            if not only_leaves:
                dump_str += "{}".format(node)
            dump_str = dump_nodes(node.sub_nodes, dump_str, only_leaves)
    return dump_str


# get id map
def get_node_id_map(node_list, id_map=None):
    if id_map is None:
        id_map = {}
    for node in node_list:
        id_map[node.id] = node
        if node.sub_nodes:
            id_map = get_node_id_map(node.sub_nodes, id_map)
    return id_map


# condition item
class ConditionItem (object):

    def __init__(self, left, right=None, operator=None):
        if operator not in ['and', 'or', 'not', None]:
            raise TypeError("unknown operator '{}'".format(operator))
        if operator in ['not', None] and right:
            raise TypeError("right param is given for operator '{}'".format(operator))
        self.left = left
        self.right = right
        self.operator = operator

    def get_dict_form(self, serial_id=None, dict_form=None):
        if dict_form is None:
            dict_form = {}
            is_entry = True
        else:
            is_entry = False
        if serial_id is None:
            serial_id = 0
        if isinstance(self.left, ConditionItem):
            serial_id, dict_form  = self.left.get_dict_form(serial_id, dict_form)
            left_id = serial_id
        else:
            left_id = str(self.left)
        if isinstance(self.right, ConditionItem):
            serial_id, dict_form = self.right.get_dict_form(serial_id, dict_form)
            right_id = serial_id
        else:
            if self.right is None:
                right_id = None
            else:
                right_id = str(self.right)
        dict_form[serial_id] = {'left': left_id, 'right': right_id, 'operator': self.operator}
        if is_entry:
            return dict_form
        else:
            return serial_id+1, dict_form
