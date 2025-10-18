from __future__ import annotations
import argparse, itertools, sys,json
from typing import List, Generator, Set, Tuple
from system_info import start_timers, stop_timers, get_system_info, pretty_print_summary

Elem = int
Table = List[List[int]]
Clos  = List[List[bool]]

def floyd_bit(tc_bits: List[int], n: int) -> None:
    changed = True
    while changed:
        changed = False
        for i in range(n):
            before = tc_bits[i]
            r = tc_bits[i]
            union = 0
            while r:
                k_mask = r & -r
                k = (k_mask.bit_length() - 1)
                union |= tc_bits[k]
                r &= r - 1
            tc_bits[i] |= union
            if tc_bits[i] != before:
                changed = True

def is_poset_with_0_1(tc_bits: List[int], n: int) -> bool:
    # reflexive
    for i in range(n):
        if not ((tc_bits[i] >> i) & 1):
            return False
    # antisymmetric
    for i in range(n):
        for j in range(i+1, n):
            if ((tc_bits[i] >> j) & 1) and ((tc_bits[j] >> i) & 1):
                return False
    # require 0 < x and x < top
    top = n-1
    for x in range(n):
        if not ((tc_bits[0] >> x) & 1): return False
        if not ((tc_bits[x] >> top) & 1): return False
    return True

# =========================
# Generate posets
# =========================
def generate_posets(n:int)->Generator[Clos,None,None]:
    pairs=[(i,j) for i in range(n) for j in range(i+1,n) if not (i==0 or j==n-1)]
    base=[0]*n
    for i in range(n):
        base[i] |= 1<<i      # reflexive
        base[0] |= 1<<i      # 0 < i
        base[i] |= 1<<(n-1)  # i < top
    def rec(k:int, tc_bits:List[int]):
        if k==len(pairs):
            tc2 = tc_bits[:]
            floyd_bit(tc2, n)
            if not is_poset_with_0_1(tc2, n): 
                return
            out = [[False]*n for _ in range(n)]
            for i in range(n):
                row = tc2[i]
                for j in range(n):
                    out[i][j] = ((row>>j)&1)==1
            yield out
            return
        i,j = pairs[k]
        # branch 1
        yield from rec(k+1, tc_bits[:])
        # branch 2: set i<j
        if ((tc_bits[i] >> j) & 1) == 0:
            tc2 = tc_bits[:]
            tc2[i] |= 1<<j
            # local propagation
            for x in range(n):
                if ((tc2[x]>>i)&1)==1:
                    tc2[x] |= 1<<j
            for y in range(n):
                if ((tc2[j]>>y)&1)==1:
                    tc2[i] |= 1<<y
            if ((tc2[j]>>i)&1)==0:
                yield from rec(k+1, tc2)
        else:
            yield from rec(k+1, tc_bits[:])
    yield from rec(0, base[:])

# =========================
# Lattice helpers
# =========================
def minimal(tc:Clos,S): return {c for c in S if not any(tc[d][c] and d!=c for d in S)}
def maximal(tc:Clos,S): return {c for c in S if not any(tc[c][d] and d!=c for d in S)}

def lattice(tc:Clos):
    n=len(tc)
    meet=[[ -1]*n for _ in range(n)]
    join=[[ -1]*n for _ in range(n)]
    for a in range(n):
        for b in range(a,n):
            upp={c for c in range(n) if tc[a][c] and tc[b][c]}
            low={c for c in range(n) if tc[c][a] and tc[c][b]}
            lub=minimal(tc,upp); glb=maximal(tc,low)
            if len(lub)!=1 or len(glb)!=1: return None
            j=next(iter(lub)); m=next(iter(glb))
            join[a][b]=join[b][a]=j; meet[a][b]=meet[b][a]=m
    return meet,join

# =========================
# Monoid with pruning
# =========================
def associative_partial(tbl:Table, known:List[List[bool]], i:int,j:int, n:int)->bool:
    a = tbl[i][j]
    for k in range(n):
        if known[a][k] and known[j][k] and known[i][tbl[j][k]]:
            if tbl[a][k] != tbl[i][ tbl[j][k] ]:
                return False
        if known[j][k] and known[i][tbl[j][k]] and known[a][k]:
            if tbl[a][k] != tbl[i][ tbl[j][k] ]:
                return False
        if known[k][i]:
            x = tbl[k][i]
            if known[x][j] and known[k][tbl[i][j]]:
                if tbl[x][j] != tbl[k][tbl[i][j]]:
                    return False
    return True

def gen_monoid(meet:Table, tc:Clos, n:int)->Generator[Table,None,None]:
    top=n-1
    base=[[-1]*n for _ in range(n)]
    known=[[False]*n for _ in range(n)]

    for i in range(n): 
        base[i][top]=base[top][i]=i; known[i][top]=known[top][i]=True
        base[i][0]=base[0][i]=0; known[i][0]=known[0][i]=True

    le = tc
    le_list = [[j for j in range(n) if le[i][j]] for i in range(n)]   # i <= j
    ge_list = [[j for j in range(n) if le[j][i]] for i in range(n)]   # j <= i

    cells = [(i,j) for i in range(n) for j in range(i,n) if base[i][j]==-1]
    cells.sort(key=lambda ij: (meet[ij[0]][ij[1]]+1, ij[0]!=ij[1], ij))

    def can_place(i:int,j:int,val:int)->bool:
        m = meet[i][j]         
        if not tc[val][m]:      
                return False

        if known[j][i] and base[j][i] != val:
            return False

        for b in le_list[i]:                
            if known[b][j]:
                vb = base[b][j]

                if not tc[val][vb]:
                    return False

        for a in ge_list[i]:                
            if known[a][j]:
                va = base[a][j]

                if not tc[va][val]:
                    return False

        for b in le_list[j]:                
            if known[i][b]:
                vb = base[i][b]
                if not tc[val][vb]:
                    return False

        for a in ge_list[j]:                
            if known[i][a]:
                va = base[i][a]
                if not tc[va][val]:
                    return False

        return True

    def place(i:int,j:int,val:int):
        base[i][j]=base[j][i]=val
        known[i][j]=known[j][i]=True

    def unplace(i:int,j:int):
        base[i][j]=base[j][i]=-1
        known[i][j]=known[j][i]=False

    def back(k:int):
        if k==len(cells):
            if all(base[base[a][b]][c]==base[a][base[b][c]] 
                   for a in range(n) for b in range(n) for c in range(n)):
                yield [row[:] for row in base]
            return
        i,j = cells[k]
        if known[i][j]:
            yield from back(k+1); return

        m = meet[i][j]
        candidates = [d for d in range(n) if tc[d][m]]

        for val in candidates:
            if not can_place(i,j,val): 
                continue
            place(i,j,val)
            if associative_partial(base, known, i, j, n):
                yield from back(k+1)
            unplace(i,j)
    yield from back(0)

# =========================
# Residuation (arrow)
# =========================
def arrow(tbl:Table,tc:Clos, caches=None):
    n=len(tbl)
    if caches is None:
        up=[0]*n; down=[0]*n
        for a in range(n):
            for b in range(n):
                if tc[a][b]: 
                    up[a]   |= 1<<b
                    down[b] |= 1<<a
        caches = (up, down)
    up, down = caches

    arr=[[0]*n for _ in range(n)]
    for a in range(n):
        for b in range(n):
            S_mask = 0
            for d in range(n):
                if (up[ tbl[a][d] ] >> b) & 1:
                    S_mask |= 1<<d
            maxima = []
            r = S_mask
            while r:
                d = (r & -r).bit_length() - 1
                # d is maximal if no e in S with d<e (approx via up-sets)
                if (S_mask & (up[d] & ~(1<<d))) == 0:
                    maxima.append(d)
                r &= r - 1
            if len(maxima)!=1:
                return None
            arr[a][b]=maxima[0]
    # verify adjointness
    for a in range(n):
        for b in range(n):
            for c in range(n):
                if tc[ tbl[a][b] ][c] != tc[b][ arr[a][c] ]:
                    return None
    return arr

# =========================
# Family checks
# =========================
def prel(arr,join,top): return all(join[arr[x][y]][arr[y][x]]==top for x in range(len(arr)) for y in range(len(arr)))
def div(tbl,arr,meet):  return all(tbl[x][arr[x][y]]==meet[x][y] for x in range(len(tbl)) for y in range(len(tbl)))

def accept_kind(want: str, has_prel: bool, has_div: bool) -> bool:
    if want == "MTL":
        return has_prel and not has_div
    if want == "DIV":
        return has_div and not has_prel
    if want == "BL":
        return has_prel and has_div
    if want == "RL":
        return not has_prel and not has_div
    if want == "ALL":
        return True
    return False

# =========================
# Isomorphism helpers
# =========================
def canon_id(tc: Clos, mul: Table, arr: Table) -> tuple:
    n = len(tc)
    best = None
    for perm in itertools.permutations(range(1, n - 1)):
        sigma = (0, *perm, n - 1)
        inv = {sigma[i]: i for i in range(n)}
        m2  = tuple(tuple(sigma[mul[inv[i]][inv[j]]] for j in range(n)) for i in range(n))
        a2  = tuple(tuple(sigma[arr[inv[i]][inv[j]]] for j in range(n)) for i in range(n))
        tc2 = tuple(tuple(tc[inv[i]][inv[j]] for j in range(n)) for i in range(n))
        # serializare canonică ca tuplu (complet fără ambiguități)
        cand = (m2, a2, tc2)
        if best is None or cand < best:
            best = cand
    return best

# =========================
# CLI
# =========================
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("n", type=int)
    ap.add_argument("kind", choices=["MTL", "DIV", "BL", "RL","ALL"],
                    help="family: MTL-pure, DIV-pure, BL (both), RL (all)")
    ap.add_argument("--count",  action="store_true",
                    help="show only summary (no tables)")
    ap.add_argument("--limit",  type=int, default=1,
                    help="max examples to print (0 = unlimited)")
    ap.add_argument("--iso",    action="store_true",
                    help="deduplicate up to isomorphism (fix 0 and 1)")
    ap.add_argument("--json-out", type=str, default="",
                    help="append accepted models incrementally to a JSON file")
    ap.add_argument("--latex-out", type=str, default="",
                    help="append accepted models incrementally to a LaTeX file")

    args = ap.parse_args()
    # Timers + system info
    t_wall_start, t_cpu_start = start_timers()
    sys_info = get_system_info()

    n, want, limit = args.n, args.kind, args.limit
    alg_type=None
    bl_cnt = mtl_cnt = div_cnt = rest_cnt = 0    
    writer = None
    if args.latex_out:
        try:
            from latex_algebra_writer import LatexAlgebraWriter
            writer = LatexAlgebraWriter(args.latex_out, title=f"Algebras (n={n}, kind={want})", make_toc=True)
        except Exception as e:
            print(f"[warn] --latex-out ignored: {e}", file=sys.stderr)
            writer = None

    if args.json_out:
        try:
            from json_algebra_writer import JSONAlgebraWriter
            json_writer = JSONAlgebraWriter(args.json_out)
        except Exception as e:
            print(f"[warn] --json-out ignored: {e}", file=sys.stderr)
            json_writer = None

    total_posets=total_lattices=total_monoids=total_tested = total_raw=total_writen = printed = 0
    classes: Set[tuple] = set()
    
    classes_bl: Set[tuple]  = set()
    classes_mtl: Set[tuple] = set()
    classes_div: Set[tuple] = set()
    classes_rest:Set[tuple] = set()


    for tc in generate_posets(n):
        total_posets+=1
        lat = lattice(tc)
        if lat is None:
            continue
        meet, join = lat
        total_lattices+=1
        for mul in gen_monoid(meet, tc, n):
            total_monoids+=1
            arr = arrow(mul, tc)
            if arr is None:
                continue
            total_tested += 1
            has_prel = prel(arr, join, n - 1)
            has_div  = div(mul, arr, meet)


            if has_prel and has_div:
                bl_cnt += 1;alg_type="BL"
            elif has_prel and not has_div:
                mtl_cnt += 1;alg_type="MTL"
            elif has_div and not has_prel:
                div_cnt += 1;alg_type="DIV"
            else:
                rest_cnt += 1;alg_type="Other RL"

            if not accept_kind(want, has_prel, has_div):
                continue
            total_raw += 1

            if args.iso:
                
                cid = canon_id(tc, mul,arr)
                if cid in classes:
                    continue        
                
                classes.add(cid)               
                if has_prel and has_div:
                    classes_bl.add(cid)
                elif has_prel and not has_div:
                    classes_mtl.add(cid)
                elif has_div and not has_prel:
                    classes_div.add(cid)
                elif not has_div and not has_prel:
                        classes_rest.add(cid)
                else:
                    pass
                                
            # Incremental LaTeX append
            total_writen+=1;
            if writer is not None:
                try:
                    writer.add_example(kind=alg_type, n=total_writen, mul=mul, arr=arr, tc=tc)
                except Exception as e:
                    print(f"[warn] failed to append LaTeX: {e}", file=sys.stderr)

            # Incremental JSON append (NDJSON)
            if json_writer is not None:
                try:
                    rec = {
                        "_type": "example",
                        "index": total_writen,
                        "n": n,
                        "kind": alg_type,
                        "has_prel": has_prel,
                        "has_div": has_div,
                        "mul": mul,
                        "arr": arr,
                        "tc": tc
                    }
                    if args.iso:
                        rec["canon_id"] = {
                            "mul": [list(row) for row in cid[0]],
                            "arr": [list(row) for row in cid[1]],
                            "tc":  [list(row) for row in cid[2]],
                        }
                    json_writer.add_example(rec)
                except Exception as e:
                    print(f"[warn] failed to append JSON: {e}", file=sys.stderr)

            if not args.count:
                printed += 1
                print(f"\n=== Example {printed} of kind {alg_type} (n={n}) ===")
                print("*:"); [print(" ".join(map(str,row))) for row in mul]
                print("->:"); [print(" ".join(map(str,row))) for row in arr]
            if 0 < limit == printed:
                break
        if 0 < limit == printed:
            break

    # SUMMARY
    if args.count:
        print(f"Total posets tested: {total_posets}")
        print(f"Total lattices tested: {total_lattices}")
        print(f"Total monoids tested: {total_monoids}")
        print(f"Total residuated  lattices tested: {total_tested}")
        print(f"Total raw models:       {total_raw}")

        total_rl_by_families = bl_cnt + mtl_cnt + div_cnt + rest_cnt
        print(f"split: BL={bl_cnt}, MTL={mtl_cnt}, DIV={div_cnt}, REST={rest_cnt}  (sum={total_rl_by_families})")


        if args.iso:
            print(f"Distinct iso-classes:   {len(classes)}")

            print(f"  BL:  {len(classes_bl)}")
            print(f"  MTL: {len(classes_mtl)}")
            print(f"  DIV: {len(classes_div)}")
            print(f"  REST:{len(classes_rest)}")
            print(f"  CHECK sum = {len(classes_bl)+len(classes_mtl)+len(classes_div)+len(classes_rest)}")
    

    timings = stop_timers(t_wall_start, t_cpu_start)


    pretty_print_summary(timings, sys_info)


    if 'writer' in locals() and writer is not None:
        try:
            summary = {
                ('iso-classes' if args.iso else 'raw-models'): (len(classes) if args.iso else total_raw),
                "timings": timings,
                "system": sys_info
            }
            writer.add_summary(summary)
            writer.close()
        except Exception as e:
            print(f"[warn] failed to finalize LaTeX: {e}", file=sys.stderr)


    if 'json_writer' in locals() and json_writer is not None:
        try:
            summary = {
                "n": n,
                "kind": want,
                "totals": {
                    "posets": total_posets,
                    "lattices": total_lattices,
                    "monoids": total_monoids,
                    "tested_rl": total_tested,
                    "raw_models": total_raw
                },
                "split": {
                    "BL": bl_cnt, "MTL": mtl_cnt, "DIV": div_cnt, "REST": rest_cnt
                },
                "timings": timings,
                "system": sys_info
            }
            if args.iso:
                summary["iso_classes"] = {
                    "total": len(classes),
                    "BL": len(classes_bl), "MTL": len(classes_mtl),
                    "DIV": len(classes_div), "REST": len(classes_rest)
                }
            json_writer.add_summary(summary)
            json_writer.close()
        except Exception as e:
            print(f"[warn] failed to finalize JSON: {e}", file=sys.stderr)


if __name__=="__main__":
    main()
