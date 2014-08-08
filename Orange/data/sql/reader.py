


class SqlReader:
    def read_file(self, filename, cls=None):
        with open(filename) as file:
            return self._read_file(file, cls)

    def _parse_header(self, header):
        header = [line.strip('% ') for line in header.split('\n')]
        connection_params = {}

        section = ''

        for line in header:
            if line == "CONNECTION":
                section = 'connection'
            elif line == "DOMAIN":
                section = 'domain'

            if section == 'connection':
                tokens = line.split(':', 1)
                if len(tokens) < 2:
                    continue
                name, value = map(str.strip, tokens)
                connection_params[name] = value

        return connection_params, {}
