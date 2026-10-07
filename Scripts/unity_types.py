"""Correct generated MonoBehaviour alignment and validate against Unity's header."""
from UnityPy.helpers.TypeTreeNode import TypeTreeNode
from UnityPy.helpers.TypeTreeGenerator import TypeTreeGenerator
from UnityPy.helpers import TypeTreeHelper
from UnityPy.streams import EndianBinaryReader
import ctypes
import importlib


class CheckedTypeTreeGenerator(TypeTreeGenerator):
    """The pinned API puts native calls inside assert; execute them also under -O."""
    def load_dll(self, dll):
        api = importlib.import_module('TypeTreeGeneratorAPI.TypeTreeGenerator')
        if api.DLL.TypeTreeGenerator_loadDLL(self.ptr, dll, len(dll)):
            raise ValueError('Failed to load analysis DLL')

    def get_nodes(self, assembly, fullname):
        api = importlib.import_module('TypeTreeGeneratorAPI.TypeTreeGenerator')
        pointer = ctypes.POINTER(api.TypeTreeNodeNative)()
        count = ctypes.c_int()
        result = api.DLL.TypeTreeGenerator_generateTreeNodesRaw(
            self.ptr, assembly.encode('ascii'), fullname.encode('ascii'),
            ctypes.byref(pointer), ctypes.byref(count))
        if result or not pointer or count.value <= 0:
            raise ValueError('Failed to generate analysis schema for '+fullname)
        try:
            array = ctypes.cast(pointer, ctypes.POINTER(api.TypeTreeNodeNative*count.value)).contents
            return [api.TypeTreeNode(m_Type=n.m_Type.decode('ascii'), m_Name=n.m_Name.decode('ascii'),
                                     m_Level=n.m_Level, m_MetaFlag=n.m_MetaFlag) for n in array]
        finally:
            api.DLL.TypeTreeGenerator_freeTreeNodesRaw(pointer, count)


def serialized_bytes(obj):
    # UnityPy get_raw_data() reads the original reader, even after set_raw_data().
    return obj.data if obj.data is not None else obj.get_raw_data()


def current_tree(obj, schema=None):
    raw = serialized_bytes(obj)
    reader = EndianBinaryReader(raw, endian=obj.reader.endian)
    return TypeTreeHelper.read_typetree(obj._get_typetree_node(schema), reader, as_dict=True,
                                       assetsfile=obj.assets_file, byte_size=len(raw), check_read=True)


def generated_tree(obj):
    # Do not accept ObjectReader's silent fallback to the base-only schema.
    node = obj.serialized_type.node if obj.serialized_type else None
    if node is None:
        node = obj.generate_monobehaviour_node()
    nodes = node.to_dict_list()
    for node in nodes:
        node.pop('m_Children', None)
        if node['m_Name'] == 'm_Enabled' and node['m_Level'] == 1:
            node['m_MetaFlag'] |= 0x4000
    schema = TypeTreeNode.from_list(nodes)
    tree = obj.read_typetree(nodes=schema)
    head = obj.parse_monobehaviour_head()
    for key in ('m_GameObject', 'm_Script'):
        pointer = getattr(head, key)
        if tree[key] != {'m_FileID': pointer.m_FileID, 'm_PathID': pointer.m_PathID}:
            raise ValueError('Generated schema disagrees with native MonoBehaviour header')
    if tree['m_Name'] != head.m_Name or tree['m_Enabled'] != head.m_Enabled:
        raise ValueError('Generated schema disagrees with native MonoBehaviour identity')
    raw = serialized_bytes(obj)
    obj.save_typetree(tree, nodes=schema)
    if serialized_bytes(obj) != raw:
        raise ValueError('Generated schema failed byte-exact no-op')
    return tree, schema
