/* -*- Mode: C++; tab-width: 2; indent-tabs-mode: nil; c-basic-offset: 2 -*-
 *
 * The contents of this file are subject to the Netscape Public
 * License Version 1.1 (the "License"); you may not use this file
 * except in compliance with the License. You may obtain a copy of
 * the License at http://www.mozilla.org/NPL/
 *
 * Software distributed under the License is distributed on an "AS
 * IS" basis, WITHOUT WARRANTY OF ANY KIND, either express or
 * implied. See the License for the specific language governing
 * rights and limitations under the License.
 *
 * The Original Code is mozilla.org code.
 *
 * The Initial Developer of the Original Code is Netscape
 * Communications Corporation.  Portions created by Netscape are
 * Copyright (C) 1999 Netscape Communications Corporation. All
 * Rights Reserved.
 *
 * Contributor(s): 
 */
#ifndef nsMacUnicodeFontInfo_h__
#define nsMacUnicodeFontInfo_h__
#include "nscore.h"
class nsMacUnicodeFontInfo {
 public:
  PRUint32* GetGlobalFontInfo();
 protected:   
  void InitGolbal();
 private:
	static PRUint32 gGlobalFontInfo[2048];
	static PRBool gGlobalFontInfoInit;
	static PRUint32 gFontsCount;
	static PRUint32 gTTFFontsCount;
	static PRUint32 gGlyphCount;
};
#endif 