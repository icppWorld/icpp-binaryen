"""Hand-curated cffi cdef: the subset of binaryen-c.h that the public API needs.

Signatures are verified against the bundled Binaryen version's binaryen-c.h
(the header ships in every official release tarball). Do NOT auto-translate
the full header — add declarations one by one, only when a new API needs them.
"""

CDEF = """
typedef uint32_t BinaryenIndex;
typedef uint32_t BinaryenExternalKind;
typedef struct BinaryenModule *BinaryenModuleRef;
typedef struct BinaryenExport *BinaryenExportRef;

BinaryenExternalKind BinaryenExternalGlobal(void);

BinaryenModuleRef BinaryenModuleRead(char *input, size_t inputSize);
void BinaryenModuleDispose(BinaryenModuleRef module);
bool BinaryenModuleValidate(BinaryenModuleRef module);
void BinaryenModuleOptimize(BinaryenModuleRef module);
void BinaryenSetOptimizeLevel(int level);
void BinaryenSetShrinkLevel(int level);

BinaryenIndex BinaryenGetNumExports(BinaryenModuleRef module);
BinaryenExportRef BinaryenGetExportByIndex(BinaryenModuleRef module,
                                           BinaryenIndex index);
BinaryenExternalKind BinaryenExportGetKind(BinaryenExportRef export_);
const char *BinaryenExportGetName(BinaryenExportRef export_);
void BinaryenRemoveExport(BinaryenModuleRef module, const char *externalName);

BinaryenIndex BinaryenGetNumGlobals(BinaryenModuleRef module);

typedef struct BinaryenModuleAllocateAndWriteResult {
  void *binary;
  size_t binaryBytes;
  char *sourceMap;
} BinaryenModuleAllocateAndWriteResult;
BinaryenModuleAllocateAndWriteResult
BinaryenModuleAllocateAndWrite(BinaryenModuleRef module,
                               const char *sourceMapUrl);
"""
