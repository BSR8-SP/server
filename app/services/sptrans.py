import os

import httpx


SPTRANS_BASE_URL = "https://api.olhovivo.sptrans.com.br/v2.1"


class SPTransError(Exception):
    pass


class SPTransClient:
    """Minimal client for the SPTrans Olho Vivo API.

    The token comes from the SPTRANS_TOKEN environment variable. The API
    authenticates with a cookie, so the same httpx client is reused for
    every call and we log in again whenever a request returns 401.
    """

    def __init__(
        self,
        token: str | None = None,
        http_client: httpx.AsyncClient | None = None,
    ):
        self.token = token if token is not None else os.getenv("SPTRANS_TOKEN")
        self.http = http_client or httpx.AsyncClient(
            base_url=SPTRANS_BASE_URL,
            timeout=10,
        )
        self.authenticated = False

    async def authenticate(self) -> None:
        if not self.token:
            raise SPTransError("SPTRANS_TOKEN is not set")

        response = await self.http.post(
            "/Login/Autenticar",
            params={"token": self.token},
        )
        # The API answers 200 with "true" or "false".
        if response.status_code != 200 or response.json() is not True:
            raise SPTransError("SPTrans authentication failed")

        self.authenticated = True

    async def get(self, path: str, params: dict) -> object:
        if not self.authenticated:
            await self.authenticate()

        try:
            response = await self.http.get(path, params=params)
            if response.status_code == 401:
                await self.authenticate()
                response = await self.http.get(path, params=params)
            response.raise_for_status()
        except httpx.HTTPError as error:
            raise SPTransError(f"SPTrans request failed: {error}") from error

        return response.json()

    async def search_lines(self, term: str) -> list[dict]:
        """Lines matching a term, one entry per direction.

        Example entry: {"cl": 1273, "lc": false, "lt": "8000", "sl": 1,
        "tl": 10, "tp": "PCA.RAMOS DE AZEVEDO", "ts": "TERMINAL LAPA"}
        """
        return await self.get("/Linha/Buscar", {"termosBusca": term})

    async def fetch_stops(self, line_id: int) -> list[dict]:
        """Stops of one line direction (cl), in route order.

        Example entry: {"cp": 340015329, "np": "AFONSO BRAZ B/C1",
        "ed": "R ARMINDA", "py": -23.592938, "px": -46.672727}
        """
        return await self.get(
            "/Parada/BuscarParadasPorLinha",
            {"codigoLinha": line_id},
        )

    async def close(self) -> None:
        await self.http.aclose()


sptrans_client = SPTransClient()


def get_sptrans_client() -> SPTransClient:
    return sptrans_client
