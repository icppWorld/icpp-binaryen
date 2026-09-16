;; Fixture for the globals-limit fix: 8 defined globals, 6 of them exported.
;; After fix_globals_limit removes the global exports and optimizes, only the
;; two globals used by `sum` survive — mirroring the production case where
;; exported globals are what keeps dead globals alive.
(module
  (memory (export "memory") 1)
  (global $g0 (mut i32) (i32.const 0))
  (global $g1 (mut i32) (i32.const 1))
  (global $g2 (mut i32) (i32.const 2))
  (global $g3 (mut i32) (i32.const 3))
  (global $g4 (mut i32) (i32.const 4))
  (global $g5 (mut i32) (i32.const 5))
  (global $g6 (mut i32) (i32.const 6))
  (global $g7 (mut i32) (i32.const 7))
  (func $sum (result i32)
    (i32.add (global.get $g0) (global.get $g1)))
  ;; Writes keep g0/g1 truly mutable, so the optimizer cannot fold them away
  (func $bump
    (global.set $g0 (i32.add (global.get $g0) (i32.const 1)))
    (global.set $g1 (i32.add (global.get $g1) (i32.const 1))))
  (export "sum" (func $sum))
  (export "bump" (func $bump))
  (export "g2" (global $g2))
  (export "g3" (global $g3))
  (export "g4" (global $g4))
  (export "g5" (global $g5))
  (export "g6" (global $g6))
  (export "g7" (global $g7))
)
