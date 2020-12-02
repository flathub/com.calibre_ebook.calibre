# calibre

<img align="left" src="https://raw.githubusercontent.com/kovidgoyal/calibre/master/resources/images/lt.png" height="200" width="200"/>

calibre is an e-book manager. It can view, convert, edit and catalog e-books 
in all of the major e-book formats. It can also talk to e-book reader 
devices. It can go out to the internet and fetch metadata for your books. 
It can download newspapers and convert them into e-books for convenient 
reading. It is cross platform, running on Linux, Windows and macOS.

For more information, see the [calibre About page](https://calibre-ebook.com/about)
and the [calibre source repository](https://github.com/kovidgoyal/calibre/).

## Flatpak-specific notes

While this calibre build tries to be as close to the official calibre binary
distribution as possible, some trade-offs are made to reuse as many libraries
from the underlying KDE Platform image as possible. In particular, this means
that the Platform's Qt version with KDE's native integration modules is used
instead the custom version shipped with the official calibre package.

The complete list of reused libraries shipped in this build may be viewed by
examining the `CALIBRE_PKG_BLACKLIST` variable of the [Flatpak dependency
generation script](deps/bypy-generated/generate.py) (read the comment above
it if you are curious about the comment-lines).

### Updating this Flatpak

To update this Flatpak to a new version, follow these steps:

  1. Perform a deep clone of this GIT repository:  
     `git clone --recursive https://github.com/flathub/com.calibre_ebook.calibre.git`
  2. Update the `bypy` submodule to the latest upstream commit:  
     `git submodule update --remote`
  3. Regenerate the list of Flatpak dependency modules from Calibre's bypy configuration:  
     `deps/bypy-generated/generate.py`
  4. Use `git diff` to review the changes the script has made
  5. Update the *sources* section of *com.calibre_ebook.calibre.yaml* to point to the new source release version and its hash.
  6. If you are able to, perform a local test-build using `flatpak-builder`:  
     `flatpak-builder --force-clean --ccache --repo repo build com.calibre_ebook.calibre.yaml`
       * If any of the patches fail to apply, check if they are still needed and, if so, fix them.
  7. Create a PR for the new version.
  8. PROFIT!

(If you get stuck at any step, please open an issue to get some feedback!)