
class FlooterError(Exception):
    def __init__(self, msg: str, enriched: bool = False) -> None:
        super().__init__(msg)
        self.is_enriched = enriched
    def enrich(self, msg: str) -> 'FlooterError':
        return FlooterError(f'{msg} {self.args[0]}', True)

    def message(self) -> str:
        return self.args[0]

class FlootSpecSyntaxError(FlooterError):
    pass

class FlooterRunError(FlooterError):
    pass