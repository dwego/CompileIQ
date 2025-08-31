# Guia de Performance em Java (Boas Práticas + Refatoração + Algoritmos)

> **Objetivo**: Consolidar práticas e padrões para que um agente de IA (ou devs) decida, de forma **orientada a evidências**, o que usar visando **tempo de execução menor** e **consumo de CPU/memória eficiente**.

---

## 0) Princípios que evitam armadilhas

* **Meça antes de otimizar**: Evite micro‑otimizações sem perfil. Use **JMH** para microbenchmarks; **Java Flight Recorder (JFR)**/**Async Profiler** para perfil em produção/homolog.
* **Complexidade > micro‑otimização**: Ganhos reais vêm de **escolher o algoritmo/estrutura correta**.
* **Dados guiam decisões**: Colete **p95/p99**, throughput e GC logs. Compare **baseline vs candidato** com repetição e warmup.
* **Localidade de dados importa**: Estruturas contíguas (arrays, `ArrayList`) tendem a ser mais cache‑friendly.
* **Evite alocações desnecessárias**: Alocação/boxing/strings imutáveis custam caro no hot path.
* **Evite trabalho em excesso**: Debounce/batch, short‑circuit, cache.

---

## 1) Metodologia de medição (JMH + perfil)

### 1.1 JMH (sugestão de esqueleto)

```java
@State(Scope.Thread)
public class MyBench {
  @Param({"1000","100000"}) int n;
  int[] a;

  @Setup(Level.Trial) public void setup() {
    a = java.util.stream.IntStream.range(0, n).toArray();
  }

  @Benchmark
  @Warmup(iterations = 3, time = 1)
  @Measurement(iterations = 5, time = 1)
  @Fork(2)
  public long sumLoop() {
    long s = 0L; for (int v: a) s += v; return s;
  }
}
```

**Boas práticas JMH**: defina warmup/measurement, gere JAR com `mvn clean install` e execute com `java -jar target/benchmarks.jar`.

### 1.2 Perfil em runtime

* **JFR**: `-XX:StartFlightRecording=filename=app.jfr,duration=60s,settings=profile`
* **Async Profiler**: chama nativo, baixe overhead; excelente p/ flamegraphs.

---

## 2) Escolha de Estruturas de Dados (guia rápido)

| Problema                     | Melhor escolha (geral)                                             | Observações                                                            |
| ---------------------------- | ------------------------------------------------------------------ | ---------------------------------------------------------------------- |
| Lista dinâmica               | `ArrayList`                                                        | Melhores leituras/iterações. `LinkedList` quase sempre pior.           |
| Conjunto sem ordem           | `HashSet`                                                          | `HashSet` >> `TreeSet` na média; `TreeSet` só se precisa de ordenação. |
| Mapa sem ordem               | `HashMap`                                                          | Para concorrência: `ConcurrentHashMap`.                                |
| Mapa ordenado                | `TreeMap`                                                          | Log N; use só se **precisa** de ordenação/navegação.                   |
| Fila de prioridade           | `PriorityQueue`                                                    | Heap binário; ótimo para **top‑K**/Dijkstra.                           |
| Fila lock‑free               | `ArrayBlockingQueue`/`LinkedBlockingQueue`/`ConcurrentLinkedQueue` | Escolha pela taxa de produtores/consumidores.                          |
| Imutáveis                    | `List.of(...)`, `Map.of(...)`                                      | Melhor para compartilhar sem cópias/locks.                             |
| Grandes sequências numéricas | `int[]/long[]`                                                     | Arrays primitivos evitam boxing e melhoram locality.                   |

### 2.1 Complexidades (média)

* `ArrayList`: acesso O(1), inserir no fim amortizado O(1), remover no meio O(n)
* `HashMap/HashSet`: put/get O(1) média; pior caso O(n) (raro com hash adequado)
* `TreeMap/TreeSet`: O(log n) para put/get/remove
* `PriorityQueue`: inserir O(log n), extrair min/max O(log n)

**Dicas**:

* **Pré‑dimensione**: `new HashMap<>(expectedSize*1.33f)`; `new ArrayList<>(capacidade)`.
* **Evite `LinkedList`**: má locality e custos de ponteiro.
* **Use primitivas**: `TIntArrayList` (fastutil) ou arrays primitivos p/ hot paths.

---

## 3) Padrões de Refatoração Eficientes

* **`String` -> `StringBuilder`** em loops:

```java
StringBuilder sb = new StringBuilder(256);
for (var s: parts) sb.append(s);
return sb.toString();
```

* **Evite boxing/unboxing**: use `int` em vez de `Integer` em cálculos intensivos.
* **Batch I/O**: Bufferize (`BufferedInputStream`, `BufferedWriter`) e evite chamadas pequenas repetidas.
* **Evite streams em hot path**: preferir loops simples quando a legibilidade permitir; `stream()` cria objetos/iteradores.
* **Remova alocações temporárias**: reutilize buffers; evite `new` em laços apertados.
* **Curto‑circuito**: cheque condições baratas primeiro.
* **Eliminar recursão profunda**: prefira iteração/stack própria para evitar overhead e StackOverflow.

---

## 4) Algoritmos vencedores por cenário

### 4.1 Busca

* **Ordenado**: **Busca binária** (`Collections.binarySearch`) O(log n)
* **Não ordenado**: **`HashSet`/`HashMap`** para membership O(1) média.

### 4.2 Top‑K (maiores/menores)

```java
// menores K: heap max tamanho K
PriorityQueue<Integer> pq = new PriorityQueue<>(Comparator.reverseOrder());
for (int x: data) {
  if (pq.size() < K) pq.offer(x);
  else if (x < pq.peek()) { pq.poll(); pq.offer(x); }
}
```

**Complexidade**: O(n log K). Para K << n, é excelente.

### 4.3 Janela deslizante (sliding window)

* **Soma/média/contagem em faixa**: O(n) usando dois ponteiros.
* **Subarray máximo**: Kadane O(n).

### 4.4 Strings

* **Concatenação**: `StringBuilder`.
* **Busca de padrão**: **KMP**/**Boyer‑Moore** para padrões conhecidos; regex apenas se necessário.

### 4.5 Grafos

* **Caminho mínimo**: Dijkstra (não negativo), BFS (não ponderado), A\* (com heurística), Bellman‑Ford (pesos negativos).
* **Conectividade**: **Union‑Find (DSU)**.

### 4.6 Ordenação

* Use o sort nativo (`Arrays.sort`, `Collections.sort`) — altamente otimizado (Dual‑Pivot Quicksort para primitivos, Timsort para objetos).

### 4.7 Cache LRU minimalista

```java
class LRU<K,V> extends LinkedHashMap<K,V> {
  private final int cap;
  LRU(int cap){ super(cap, 0.75f, true); this.cap = cap; }
  @Override protected boolean removeEldestEntry(Map.Entry<K,V> e){ return size()>cap; }
}
```

### 4.8 Rate Limiter (Token Bucket simples)

```java
class TokenBucket {
  private final long cap, rate;
  private double tokens;
  private long last;
  TokenBucket(long cap,long rate){this.cap=cap;this.rate=rate;this.tokens=cap;this.last=System.nanoTime();}
  synchronized boolean allow(){
    long now=System.nanoTime();
    tokens=Math.min(cap, tokens + (now-last)*rate/1e9);
    last=now;
    if(tokens>=1){tokens-=1; return true;}
    return false;
  }
}
```

---

## 5) Concorrência e Paralelismo

* **Evite `parallelStream()` por padrão**: só ajuda com CPU‑bound, coleções grandes e sem contention.
* **Escolha Executor apropriado**: `newFixedThreadPool` p/ CPU‑bound \~= nº de cores; `newCachedThreadPool` para I/O‑bound com cuidado.
* **`CompletableFuture`** para compor pipelines assíncronos sem bloquear.
* **`ConcurrentHashMap`** em vez de `synchronized` global em acessos intensos.
* **False sharing**: separe contadores por cache line (ex.: `@Contended` em JDK interno ou padding manual).
* **Fork/Join**: útil para dividir/ conquistar com tarefas grandes e independentes.

Exemplo (Compose non‑blocking):

```java
CompletableFuture<Integer> f = supplyAsync(() -> loadA())
  .thenCombineAsync(supplyAsync(() -> loadB()), Integer::sum);
```

---

## 6) I/O e Serialização

* **Bufferize tudo**: `BufferedInputStream/BufferedOutputStream`.
* **NIO**: `FileChannel` + `MappedByteBuffer` para arquivos grandes.
* **Evite `ObjectOutputStream`** em hot path; prefira **JSON binário**/protobuf/flatbuffers quando performance for crítica.
* **Batch**: agrupe writes pequenos.

---

## 7) Memória e GC (visão prática)

* **Escolha do GC** (Java 17+):

  * **G1** (default): bom para heaps médios/grandes, pausas previsíveis.
  * **ZGC/Shenandoah**: latência ultra‑baixa; use se p99 de pausa é crítico.
* **Flags úteis (ponto de partida, ajustar com perfil)**:

  * `-XX:+UseG1GC` (se não default), `-Xms=X -Xmx=X` (fixar heap), `-XX:MaxGCPauseMillis=200` (tentar target), `-XX:+PrintGCDetails -Xlog:gc*` (Java 11+ usa Unified Logging: `-Xlog:gc`)
* **Menos objetos** = menos pressão de GC. Prefira arrays primitivos, reuse buffers, evite lambdas no hot path se gerarem capturas.
* **Escape analysis** permite alocar em stack (JIT); evite campos que escapam desnecessariamente.

---

## 8) Checklists de PR focados em performance

**Coleção/Algoritmo**

* [ ] A estrutura é adequada? (`ArrayList` vs `LinkedList`, `HashMap` vs `TreeMap`)
* [ ] Pré‑dimensionou coleções? (`initialCapacity`)
* [ ] Evitou boxing/unboxing?
* [ ] Evitou concatenação de `String` em loop? (use `StringBuilder`)

**Concorrência**

* [ ] `parallelStream` é realmente benéfico? (dados grandes, CPU‑bound)
* [ ] Usou `CompletableFuture`/`ExecutorService` corretamente (tamanho de pool)?
* [ ] Contenção em locks minimizada? (`ConcurrentHashMap`, sharding)

**I/O**

* [ ] Leituras/escritas bufferizadas?
* [ ] Serialização eficiente (evitar objetos pesados)?

**GC/Alocação**

* [ ] Evitou alocações temporárias em laço apertado?
* [ ] Reuso de buffers aplicado?
* [ ] Heap e GC configurados e observados com métricas?

**Medição**

* [ ] JMH com warmup/measurement/fork?
* [ ] Perfil (JFR/async‑profiler) antes/depois e regressões em p95/p99?

---

## 9) Padrões "quando usar o quê" (heurísticas rápidas)

* **Coleções pequenas (≤1e3) e leitura intensa** → `ArrayList` + loops simples.
* **Membership test frequente** → `HashSet`/`BitSet` (se IDs pequenos).
* **Ordenação eventual e navegação por intervalo** → `TreeMap/TreeSet`.
* **Top‑K com K≪N** → `PriorityQueue` (heap) ou seleção parcial.
* **Joins/dedup massivos** → Hashing + streaming; evite `distinct()` em streams se no hot path.
* **CPU‑bound puro** → `ForkJoinPool` com tarefas grandes; estabeleça granulação para evitar overhead.
* **I/O‑bound** → mais threads não ajudam CPU; use async/NIO e backpressure.

---

## 10) Anti‑padrões que degradam tempo

* `LinkedList` para iteração/índice.
* `String` concat em loop.
* Uso indiscriminado de `stream().map(...).filter(...).collect(...)` em hot path.
* Criar `Random` por chamada (use `ThreadLocalRandom`).
* Excessos de sincronização ampla (`synchronized` em método inteiro) sem necessidade.
* Serialização padrão Java em pipelines críticos.

---

## 11) Snippets úteis (otimizados e idiomáticos)

### 11.1 Binary Search seguro

```java
int idx = Collections.binarySearch(list, key);
if (idx >= 0) { /* found */ } else { /* insert at -(idx+1) */ }
```

### 11.2 Prefix Sum (soma em faixa O(1))

```java
long[] pref = new long[n+1];
for (int i=0;i<n;i++) pref[i+1]=pref[i]+a[i];
long sum(int l,int r){return pref[r]-pref[l];}
```

### 11.3 Union‑Find (DSU)

```java
class DSU {int[] p,r;DSU(int n){p=new int[n];r=new int[n];for(int i=0;i<n;i++)p[i]=i;}
int f(int x){return p[x]==x?x:(p[x]=f(p[x]));}
void u(int a,int b){a=f(a);b=f(b);if(a==b)return; if(r[a]<r[b])p[a]=b;else if(r[a]>r[b])p[b]=a;else{p[b]=a;r[a]++;}}
}
```

### 11.4 Fast I/O (leitura de arquivo grande)

```java
try (var ch = FileChannel.open(Path.of("file.dat"), StandardOpenOption.READ)) {
  var mb = ch.map(FileChannel.MapMode.READ_ONLY, 0, ch.size());
  for (int i=0;i<mb.limit();i++) { byte b = mb.get(i); /* processa */ }
}
```

### 11.5 Evitar boxing em contadores

```java
long sum = 0L; for (int v: a) sum += v; // evite Long/Integer aqui
```

---

## 12) Pipeline recomendado para sua IA decidir “o melhor”

1. **Features do problema**: tamanho N, tipo de acesso (randômico/sequencial), necessidade de ordenação, percentuais de leitura vs escrita, CPU‑bound vs I/O‑bound, limites de latência p95.
2. **Regras/heurísticas** (Se‑então) baseadas nas seções 2, 4, 9 e 10.
3. **Geração de candidatos**: (ex.: `ArrayList` + loop vs `stream`, `HashMap` vs `TreeMap`).
4. **Execução de microbench (JMH)** sobre amostras realistas.
5. **Escolha baseada em evidências**: menor p95/p99, menores alocações, ausência de outliers.
6. **Feedback loop**: registre métricas no repositório de knowledge (dataset de decisões).

**Exemplo de regra**:

* *Se* N>1e6 e apenas membership → `HashSet` com `initialCapacity ≈ N/0.75`.
* *Se* precisa navegar por intervalos ordenados → `TreeMap`.
* *Se* top‑K com K≪N → heap (`PriorityQueue`).
* *Se* concatenação intensa de strings → `StringBuilder` com buffer.

---

## 13) Template de decisão (para a IA preencher)

```
Problema: __________________________
N / distribuição: __________________
Leitura/Escrita (%): ______________
Ordenação necessária? __ Sim __ Não
Latência alvo p95: ________________
Bound: __ CPU __ I/O __ Misto

Candidatos:
1) ________________________________
2) ________________________________

Medições (JMH/JFR):
- p50/p95/p99: ____________________
- Alocações/op: ___________________
- GC pausas: ______________________

Escolha: __________________________
Justificativa: ____________________
```

---

## 14) Próximos passos

* Criar um **repositório** de benchmarks canônicos (datasets, tamanhos e cenários) para reuso pela IA.
* Instrumentar a aplicação com **JFR** e exportar métricas p/ treinar as regras (ou supervisão) do agente.
* Adicionar **mais recipes** específicos ao seu domínio (ex.: parse de logs, dedup, agregações temporais, joins por chave).

> **Dica**: padronize a coleta e a apresentação (CSV/JSON) dos resultados para facilitar comparações automáticas pela IA.