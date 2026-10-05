# Busca no SGS do Banco Central a taxa de desemprego (24369) e o
# rendimento medio real (24382) e grava em mercado_trabalho.csv.
# Se o BCB nao responder, para sem tocar no arquivo existente.
$ErrorActionPreference = 'Stop'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$pasta   = Split-Path -Parent $MyInvocation.MyCommand.Path
$destino = Join-Path $pasta 'mercado_trabalho.csv'
$temp    = Join-Path $pasta 'mercado_trabalho.tmp'

function Get-Serie($codigo) {
    $url = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.$codigo/dados?formato=json"
    try {
        $dados = Invoke-RestMethod -Uri $url -TimeoutSec 60
    } catch {
        throw "O Banco Central nao respondeu para a serie $codigo ($($_.Exception.Message)). Nada foi gravado."
    }
    if (-not $dados -or $dados.Count -eq 0) { throw "A serie $codigo veio vazia. Nada foi gravado." }
    $mapa = @{}
    foreach ($d in $dados) { $mapa[$d.data] = $d.valor }
    return $mapa
}

$desemprego = Get-Serie 24369
$rendimento = Get-Serie 24382

$datas = ($desemprego.Keys + $rendimento.Keys) | Sort-Object -Unique |
    Sort-Object { [datetime]::ParseExact($_, 'dd/MM/yyyy', $null) }

$linhas = @('data;taxa_desemprego;rendimento_medio_real')
foreach ($dt in $datas) {
    $iso = [datetime]::ParseExact($dt, 'dd/MM/yyyy', $null).ToString('yyyy-MM-dd')
    $linhas += "$iso;$($desemprego[$dt]);$($rendimento[$dt])"
}

# Grava primeiro num arquivo temporario e so depois substitui o definitivo
$linhas | Set-Content -Path $temp -Encoding UTF8
Move-Item -Path $temp -Destination $destino -Force

Write-Output "Meses gravados: $($datas.Count)"
Write-Output "Primeiro: $($linhas[1])"
Write-Output "Ultimo:   $($linhas[-1])"
