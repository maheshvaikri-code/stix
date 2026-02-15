"""
RESP Protocol Implementation
============================

Redis Serialization Protocol (RESP) for drop-in Redis compatibility.
"""

import asyncio
import json
from typing import Any, List, Optional, Tuple, Union

from ..cache import ISONCache
from ..graph_cache import ISONGraphCache


class RESPProtocol:
    """
    Redis Serialization Protocol (RESP) handler.

    Supports RESP2/RESP3 for Redis client compatibility.
    """

    def __init__(self, cache: ISONCache, graph_cache: Optional[ISONGraphCache] = None):
        self.cache = cache
        self.graph_cache = graph_cache or ISONGraphCache()

    def parse_request(self, data: bytes) -> Tuple[str, List[Any]]:
        """
        Parse RESP request into command and arguments.

        Returns:
            Tuple of (command, args)
        """
        if not data:
            raise ValueError("Empty request")

        # RESP array format: *<count>\r\n$<len>\r\n<data>\r\n...
        lines = data.split(b'\r\n')

        if not lines[0].startswith(b'*'):
            # Inline command format
            parts = data.decode().strip().split()
            if parts:
                return parts[0].upper(), parts[1:]
            raise ValueError("Invalid request format")

        # Parse array
        count = int(lines[0][1:])
        args = []
        idx = 1

        for _ in range(count):
            if idx >= len(lines):
                break

            if lines[idx].startswith(b'$'):
                length = int(lines[idx][1:])
                idx += 1
                if idx < len(lines):
                    args.append(lines[idx].decode()[:length])
                idx += 1
            else:
                args.append(lines[idx].decode())
                idx += 1

        if not args:
            raise ValueError("No command in request")

        return args[0].upper(), args[1:]

    def format_response(self, value: Any) -> bytes:
        """Format response in RESP format"""
        if value is None:
            return b'$-1\r\n'  # Null bulk string
        elif isinstance(value, bool):
            return b'+OK\r\n' if value else b'-ERR\r\n'
        elif isinstance(value, int):
            return f':{value}\r\n'.encode()
        elif isinstance(value, str):
            return f'${len(value)}\r\n{value}\r\n'.encode()
        elif isinstance(value, bytes):
            return f'${len(value)}\r\n'.encode() + value + b'\r\n'
        elif isinstance(value, list):
            parts = [f'*{len(value)}\r\n'.encode()]
            for item in value:
                parts.append(self.format_response(item))
            return b''.join(parts)
        elif isinstance(value, dict):
            # RESP3 map format (fallback to bulk string JSON)
            json_str = json.dumps(value)
            return f'${len(json_str)}\r\n{json_str}\r\n'.encode()
        elif isinstance(value, Exception):
            return f'-ERR {str(value)}\r\n'.encode()
        else:
            s = str(value)
            return f'${len(s)}\r\n{s}\r\n'.encode()

    def handle_command(self, command: str, args: List[str]) -> Any:
        """
        Handle a Redis command.

        Supports common Redis commands plus ISONCache extensions.
        """
        # Basic Key-Value Commands
        if command == 'SET':
            if len(args) < 2:
                return Exception("wrong number of arguments for 'set' command")

            key, value = args[0], args[1]
            ttl = None

            # Parse SET options (EX, PX, NX, XX)
            i = 2
            while i < len(args):
                opt = args[i].upper()
                if opt == 'EX' and i + 1 < len(args):
                    ttl = int(args[i + 1])
                    i += 2
                elif opt == 'PX' and i + 1 < len(args):
                    ttl = int(args[i + 1]) // 1000
                    i += 2
                else:
                    i += 1

            # Try to parse value as JSON
            try:
                parsed = json.loads(value)
            except json.JSONDecodeError:
                parsed = value

            self.cache.set(key, parsed, ttl=ttl)
            return True

        elif command == 'GET':
            if len(args) < 1:
                return Exception("wrong number of arguments for 'get' command")

            result = self.cache.get(args[0], format="ison")
            return result

        elif command == 'GETISON':
            # ISONCache extension: get with token limit
            if len(args) < 1:
                return Exception("wrong number of arguments for 'getison' command")

            max_tokens = int(args[1]) if len(args) > 1 else None
            return self.cache.get(args[0], max_tokens=max_tokens, format="ison")

        elif command == 'GETRAW':
            # Get raw JSON value
            if len(args) < 1:
                return Exception("wrong number of arguments")

            result = self.cache.get_raw(args[0])
            if result is None:
                return None
            return json.dumps(result)

        elif command == 'DEL':
            count = 0
            for key in args:
                if self.cache.delete(key):
                    count += 1
            return count

        elif command == 'EXISTS':
            count = 0
            for key in args:
                if self.cache.exists(key):
                    count += 1
            return count

        elif command == 'KEYS':
            pattern = args[0] if args else '*'
            return self.cache.keys(pattern)

        elif command == 'SCAN':
            cursor = int(args[0]) if args else 0
            pattern = '*'
            count = 100

            i = 1
            while i < len(args):
                if args[i].upper() == 'MATCH' and i + 1 < len(args):
                    pattern = args[i + 1]
                    i += 2
                elif args[i].upper() == 'COUNT' and i + 1 < len(args):
                    count = int(args[i + 1])
                    i += 2
                else:
                    i += 1

            next_cursor, keys = self.cache.scan(pattern, count, cursor)
            return [str(next_cursor), keys]

        elif command == 'TTL':
            if len(args) < 1:
                return Exception("wrong number of arguments for 'ttl' command")

            ttl = self.cache.ttl(args[0])
            if ttl is None:
                return -2  # Key doesn't exist
            return ttl if ttl > 0 else -1

        elif command == 'EXPIRE':
            if len(args) < 2:
                return Exception("wrong number of arguments for 'expire' command")

            success = self.cache.expire(args[0], int(args[1]))
            return 1 if success else 0

        elif command == 'PERSIST':
            if len(args) < 1:
                return Exception("wrong number of arguments for 'persist' command")

            success = self.cache.persist(args[0])
            return 1 if success else 0

        elif command == 'MSET':
            if len(args) < 2 or len(args) % 2 != 0:
                return Exception("wrong number of arguments for 'mset' command")

            items = {}
            for i in range(0, len(args), 2):
                try:
                    items[args[i]] = json.loads(args[i + 1])
                except json.JSONDecodeError:
                    items[args[i]] = args[i + 1]

            self.cache.mset(items)
            return True

        elif command == 'MGET':
            result = self.cache.mget(args)
            return result

        # ISONCache Extensions
        elif command == 'BUDGET':
            # BUDGET pattern token_budget [PRIORITY hits|recent|oldest|tokens]
            if len(args) < 2:
                return Exception("wrong number of arguments for 'budget' command")

            from ..schema import Priority
            pattern = args[0]
            budget = int(args[1])
            priority = Priority.HITS

            if len(args) > 2 and args[2].upper() == 'PRIORITY':
                priority_str = args[3].upper() if len(args) > 3 else 'HITS'
                try:
                    priority = Priority[priority_str]
                except KeyError:
                    priority = Priority.HITS

            result = self.cache.get_within_budget(pattern, budget, priority)
            return {
                "ison": result.ison,
                "tokens_used": result.tokens_used,
                "keys_included": result.keys_included,
                "truncated": result.truncated,
            }

        elif command == 'GRAPHSET':
            # GRAPHSET key entities_json relations_json [EX seconds]
            if len(args) < 3:
                return Exception("wrong number of arguments for 'graphset' command")

            key = args[0]
            entities = json.loads(args[1])
            relations = json.loads(args[2])
            ttl = None

            if len(args) > 3 and args[3].upper() == 'EX':
                ttl = int(args[4]) if len(args) > 4 else None

            self.graph_cache.set_graph(key, entities, relations, ttl=ttl)
            return True

        elif command == 'GRAPHGET':
            if len(args) < 1:
                return Exception("wrong number of arguments for 'graphget' command")

            max_tokens = int(args[1]) if len(args) > 1 else None
            return self.graph_cache.get_graph(args[0], max_tokens=max_tokens)

        elif command == 'TRAVERSE':
            # TRAVERSE entity [HOPS n] [TYPES type1,type2] [BUDGET n] [DIRECTION out|in|both]
            if len(args) < 1:
                return Exception("wrong number of arguments for 'traverse' command")

            entity = args[0]
            max_hops = 2
            relation_types = None
            token_budget = None
            direction = "out"

            i = 1
            while i < len(args):
                opt = args[i].upper()
                if opt == 'HOPS' and i + 1 < len(args):
                    max_hops = int(args[i + 1])
                    i += 2
                elif opt == 'TYPES' and i + 1 < len(args):
                    relation_types = args[i + 1].split(',')
                    i += 2
                elif opt == 'BUDGET' and i + 1 < len(args):
                    token_budget = int(args[i + 1])
                    i += 2
                elif opt == 'DIRECTION' and i + 1 < len(args):
                    direction = args[i + 1].lower()
                    i += 2
                else:
                    i += 1

            result = self.graph_cache.traverse(
                entity, max_hops, relation_types, token_budget, direction
            )
            return {
                "ison": result.ison,
                "tokens": result.tokens_used,
                "entities": result.entities_included,
                "hops": result.hops_traversed,
            }

        # Server Commands
        elif command == 'PING':
            return 'PONG' if not args else args[0]

        elif command == 'ECHO':
            return args[0] if args else ''

        elif command == 'INFO':
            info = self.cache.info()
            lines = [
                "# ISONCache",
                f"version:1.0.0",
                f"entries:{info['entries']}",
                f"tokens:{info['tokens']}",
                f"memory_mb:{info['memory_mb']}",
                f"hit_rate:{info['hit_rate']}",
                f"eviction_policy:{info['eviction_policy']}",
            ]
            return '\n'.join(lines)

        elif command == 'DBSIZE':
            return len(self.cache)

        elif command == 'FLUSHALL' or command == 'FLUSHDB':
            count = self.cache.clear()
            self.graph_cache.clear()
            return True

        elif command == 'COMMAND':
            # Return list of supported commands
            return ['SET', 'GET', 'DEL', 'EXISTS', 'KEYS', 'TTL', 'EXPIRE',
                    'MGET', 'MSET', 'SCAN', 'PING', 'INFO', 'DBSIZE',
                    'GETISON', 'BUDGET', 'GRAPHSET', 'GRAPHGET', 'TRAVERSE']

        elif command == 'QUIT':
            return True

        else:
            return Exception(f"unknown command '{command}'")


class RESPServerProtocol(asyncio.Protocol):
    """Asyncio protocol for RESP server"""

    def __init__(self, handler: RESPProtocol):
        self.handler = handler
        self.transport = None
        self.buffer = b''

    def connection_made(self, transport):
        self.transport = transport

    def data_received(self, data: bytes):
        self.buffer += data

        # Process complete commands
        while b'\r\n' in self.buffer:
            try:
                command, args = self.handler.parse_request(self.buffer)
                result = self.handler.handle_command(command, args)
                response = self.handler.format_response(result)
                self.transport.write(response)

                # Clear processed data (simplified - assumes one command)
                self.buffer = b''

                if command == 'QUIT':
                    self.transport.close()

            except Exception as e:
                response = self.handler.format_response(Exception(str(e)))
                self.transport.write(response)
                self.buffer = b''
                break


async def start_resp_server(
    host: str = '127.0.0.1',
    port: int = 6380,
    cache: Optional[ISONCache] = None,
    graph_cache: Optional[ISONGraphCache] = None,
) -> asyncio.Server:
    """
    Start RESP protocol server.

    Args:
        host: Server host
        port: Server port (6380 default, different from Redis)
        cache: ISONCache instance (creates new if None)
        graph_cache: ISONGraphCache instance

    Returns:
        asyncio.Server instance
    """
    cache = cache or ISONCache()
    graph_cache = graph_cache or ISONGraphCache()
    handler = RESPProtocol(cache, graph_cache)

    loop = asyncio.get_event_loop()
    server = await loop.create_server(
        lambda: RESPServerProtocol(handler),
        host, port
    )

    print(f"ISONCache RESP server listening on {host}:{port}")
    return server


def run_server(host: str = '127.0.0.1', port: int = 6380):
    """Run the RESP server (blocking)"""
    async def main():
        server = await start_resp_server(host, port)
        await server.serve_forever()

    asyncio.run(main())


if __name__ == '__main__':
    run_server()
