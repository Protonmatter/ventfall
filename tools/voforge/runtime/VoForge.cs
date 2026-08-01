// voforge runtime — Unity C# consumer (reference implementation).
//
//   string path = VoForge.Path("vo", "voss", "Four drones and a rig older than I am.");
//   StartCoroutine(VoForge.Play(this, audioSource, path, onMissing: () => { /* TTS fallback */ }));
//
// The hash must match voforge's Python djb2 exactly; it is computed over the
// UTF-8 bytes of "who|text".

using System.Text;

public static class VoForge
{
    public static string Hash(string who, string text)
    {
        byte[] bytes = Encoding.UTF8.GetBytes(who + "|" + text);
        uint h = 5381;
        unchecked
        {
            foreach (byte b in bytes) h = (h * 33) ^ b;
        }
        return h.ToString("x8");
    }

    public static string Path(string baseDir, string who, string text)
        => $"{baseDir}/{Hash(who, text)}.mp3";

#if UNITY_5_3_OR_NEWER
    public static System.Collections.IEnumerator Play(
        UnityEngine.MonoBehaviour host,
        UnityEngine.AudioSource source,
        string url,
        System.Action onMissing = null)
    {
        using (var req = UnityEngine.Networking.UnityWebRequestMultimedia.GetAudioClip(
                   url, UnityEngine.AudioType.MPEG))
        {
            yield return req.SendWebRequest();
            if (req.result != UnityEngine.Networking.UnityWebRequest.Result.Success)
            {
                onMissing?.Invoke();
                yield break;
            }
            source.clip = UnityEngine.Networking.DownloadHandlerAudioClip.GetContent(req);
            source.Play();
        }
    }
#endif
}
