from Orange.data.sql.table import SqlTable
from Orange.data import DiscreteVariable, ContinuousVariable


class SqlReader:
    def read_file(self, filename, cls=None):
        with open(filename) as file:
            return self._read_file(file, cls)

    def _read_file(self, file, cls=SqlTable):
        header, sql = self._split(file)
        connection_params, domain_params = self._parse_header(header)
        type_hints = self._parse_domain_params(domain_params)
        if sql.strip():
            connection_params['sql'] = sql
        return cls(type_hints=type_hints, **connection_params)

    @staticmethod
    def _split(file):
        header, body = [], []
        for line in file:
            if line.strip().startswith('%'):
                header.append(line)
            else:
                body.append(line)
        return "\n".join(header), "\n".join(body)

    @staticmethod
    def _parse_header(header):
        header = [line.strip('% ') for line in header.split('\n')]
        connection_params = {}
        domain_hints = {}

        section = None
        for line in header:

            if line == "CONNECTION":
                section = connection_params
            elif line == "DOMAIN":
                section = domain_hints

            if section is not None:
                tokens = line.split(':', 1)
                if len(tokens) < 2:
                    continue
                name, value = map(str.strip, tokens)
                section[name] = value

        return connection_params, domain_hints

    @staticmethod
    def _parse_domain_params(domain_params):
        type_hints = {}

        for name, hint in domain_params.items():
            modifiers = set()
            if not hint.endswith('}'):
                tokens = hint.rsplit(' ')
                if len(tokens) == 2:
                    hint, modifiers = tokens
                    modifiers = set(
                        m[0] for m in modifiers.lower().split(', ') if m)

            if hint.lower().startswith('d'):
                type_hints[name] = DiscreteVariable(name)
            if hint.lower().startswith('c'):
                type_hints[name] = ContinuousVariable(name)
            if hint.lower().startswith('{'):
                values = [v.strip()
                          for v in hint.strip('{}').split(',')]
                type_hints[name] = DiscreteVariable(name, values)

            if 'c' in modifiers:
                type_hints.setdefault('__classvars__', []).append(name)
            if 'm' in modifiers:
                type_hints.setdefault('__metas__', []).append(name)

        return type_hints

