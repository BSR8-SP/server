# server
Backend do projeto BSR8-SP

## API da SPTrans (Olho Vivo)

As rotas do mapa usam a API Olho Vivo da SPTrans. Peça um token gratuito em
https://www.sptrans.com.br/desenvolvedores e defina a variável de ambiente
antes de subir o servidor (nunca coloque o token no código):

```bash
export SPTRANS_TOKEN="seu-token"
uvicorn app.main:app --reload
```

Rotas do mapa:

- `GET /maps/fetch_bus_lines?search=875A`: linhas cujo código ou nome de terminal contém `search`, uma por sentido.
- `GET /maps/fetch_route?bus_line_code=875A-10&direction=1`: trajeto e paradas da linha em GeoJSON, pronto para o Leaflet. O `index` de cada parada define os trechos.

### Traçado das linhas (GTFS)

O `fetch_route` desenha o trajeto pelas ruas usando o GTFS da SPTrans. Baixe o
GTFS na área de desenvolvedores da SPTrans e copie `trips.txt` e `shapes.txt`
para `data/gtfs/` (ou aponte outra pasta com a variável `GTFS_DIR`). A pasta
`data/gtfs/` está no `.gitignore` porque os arquivos são grandes.

Sem esses arquivos, ou se a linha não estiver no GTFS, o trajeto liga as
paradas em linha reta. A propriedade `source` do trajeto diz qual foi usado
(`gtfs` ou `stops`).
