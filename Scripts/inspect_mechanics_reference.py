"""Read-only, pinned official-localization and managed-code mechanics evidence."""
import argparse
import hashlib
import json
from pathlib import Path
import UnityPy
import dnfile
from dncil.cil.body import CilMethodBody
from dncil.cil.body.reader import CilMethodBodyReaderBytes
from probe_assets import ROOT, digest, require


def inspect(output):
    require(output.is_relative_to(ROOT / 'outputs') and not output.exists(), 'Use a new canonical reference receipt')
    state = json.loads((ROOT / 'Documentation/localization-state.json').read_text())
    game = Path(state['sourceRoot'])
    radio = json.loads((ROOT / 'Resources/Localization/radio-source-v1.json').read_text())
    ids = {r['id'] for r in radio['entries']}
    foreigner = json.loads((ROOT / 'Resources/Localization/foreigner-source-v1.json').read_text())
    nightmare = next(r['id'] for r in foreigner['entries'] if r['key'].endswith('Asking_1_09c22e5'))
    official, inputs = [], {}
    for relative, expected in state['sourceInputs'].items():
        if '/localization-string-tables-' not in relative:
            continue
        path = game / relative
        require(digest(path) == expected, 'Official input changed: ' + relative)
        inputs[relative] = expected
        tables = {}
        for obj in UnityPy.load(str(path)).objects:
            if obj.type.name != 'MonoBehaviour':
                continue
            tree = obj.read_typetree()
            if 'm_TableData' not in tree:
                continue
            name = tree['m_Name'].split('_', 1)[0]
            if name in {'UI', 'Dialogs'}:
                require(name not in tables, 'Duplicate official table')
                tables[name] = (tree['m_LocaleId']['m_Code'], {r['m_Id']: r['m_Localized'] for r in tree['m_TableData']})
        require(set(tables) == {'UI', 'Dialogs'}, 'Official table missing')
        code, ui = tables['UI']
        dialogue_code, dialogue = tables['Dialogs']
        require(code == dialogue_code and ids <= dialogue.keys(), 'Official radio coverage differs')
        official.append({'locale': code, 'bundle': relative, 'sha256': expected,
                         'radioNoise': ui[56531188432228352], 'radioRows': len(ids),
                         'foreignerNightmare': dialogue[nightmare]})
    require(len(official) == 18, 'Expected all 18 official locales')
    relative = 'NoImNotAHuman_BackUpThisFolder_ButDontShipItWithYourGame/Managed/Assembly-CSharp.dll'
    managed = game / relative
    require(digest(managed) == state['sourceInputs'][relative], 'Managed reference changed')
    inputs[relative] = digest(managed)
    pe = dnfile.dnPE(str(managed))
    evidence = []
    for type_row in pe.net.mdtables.TypeDef:
        type_name = str(type_row.TypeName)
        if type_name not in {'RadioModel', 'RadioCloseUpView', 'StringExtensions'}:
            continue
        for item in type_row.MethodList:
            method = item.row
            name = str(method.Name)
            if type_name == 'RadioCloseUpView' and name not in {'Show', 'OnKnobValueChanged', 'OnRadioButtonPressed', 'OnMessageLineFinished'}:
                continue
            if type_name == 'StringExtensions' and name != 'ToMonospace':
                continue
            if not method.Rva:
                continue
            body = CilMethodBody(CilMethodBodyReaderBytes(pe.get_data(method.Rva)))
            instructions = []
            for ins in body.instructions:
                arg = ins.operand
                if hasattr(arg, 'table'):
                    if arg.table == 0x70:
                        arg = pe.net.user_strings.get(arg.rid).value
                    else:
                        table = pe.net.mdtables.tables.get(arg.table)
                        arg = str(getattr(table.rows[arg.rid - 1], 'Name', arg)) if table else str(arg)
                elif arg is not None and not isinstance(arg, (int, float, str)):
                    arg = str(arg)
                instructions.append({'offset': ins.offset, 'opcode': str(ins.opcode), 'operand': arg})
            evidence.append({'type': str(type_row.TypeNamespace) + '.' + type_name, 'method': name,
                             'rva': method.Rva, 'instructions': instructions})
    require(all(digest(game / relative) == expected for relative, expected in inputs.items()), 'Reference changed during inspection')
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({'schemaVersion': 1, 'gameVersion': state['gameVersion'], 'buildGuid': state['buildGuid'],
                                 'sourceRoot': str(game), 'inputs': inputs, 'officialLocales': official, 'managedEvidence': evidence,
                                 'inspectorSha256': digest(Path(__file__)), 'boundary': 'static original tables and backup managed IL; excludes live IL2CPP execution',
                                 'sourceUnchanged': True}, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'officialLocales': len(official), 'managedMethods': len(evidence), 'receipt': str(output.relative_to(ROOT))}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    inspect(parser.parse_args().output.resolve())
