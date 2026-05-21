#pragma once

// Windows-only build shim for the unmodified lacam2 upstream.
// The upstream code assumes Unix-style `uint` and alternative token support.
using uint = unsigned int;

#ifdef _MT
#undef _MT
#endif

#ifndef or
#define or ||
#endif
